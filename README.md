# DarkSword-Kit — iOS 真实利用链

目标:一条**真能打 iOS 设备**的 DarkSword 完整利用链。

## 组成（真实度分级）

| 模块 | 来源 | 状态 |
| --- | --- | --- |
| `kexploit/main.m` | **真实内核利用** — opa334 的 Objective-C 重写版，Kev1nLevin 补了 iOS 18.4 已验证偏移（iPhone 15 Pro / A17 Pro, xnu-11417.102.9） | ✅ 真代码，偏移已验证；未上真机测试（上游状态如此） |
| `kexploit/entitlements.plist` | 真实所需私有授权（no-sandbox、IOSurfaceRoot 等 IOKit user client） | ✅ |
| `c2/server.py` + `c2_config.json` | 自研 C2，双向通信 | ✅ 本机回归测试通过 |
| `implant/implant.js` | JS 后门（战利品抽取 + 任务拉取） | ✅ 协议完整 |
| `js/rce_gc.js` `rce_jit.js` | 浏览器侧 WebKit RCE 入口（JSC GC UAF / JIT 类型混淆） | ⚠️ 按公开 CVE 描述的教学实现，未真机验证 |
| `src/stage2~4*.c` | 沙箱逃逸阶段骨架 | ⚠️ 教学骨架 |

## 利用链（部署形态决定入口）

```
[形态 A: 独立二进制]                 [形态 B: 浏览器零点击]
  签好 entitlements 的 kexploit        水坑页 → js/rce_gc.js (WebKit RCE)
  直接在设备上跑 →                      → stage2/3 沙箱逃逸 →
  内核任意读写 (early_kread64/write64)  内核利用 (kexploit 逻辑)
  → kernel_base + KASLR slide          → 内核任意读写
         ↓                                    ↓
  注入 implant.js 到系统进程 ←—————————————┘
         ↓
  C2 (c2/server.py) 收战利品 / 推 JS 任务
```

## 内核利用原理（真实实现）

1. IOSurface (`PurpleGfxMem`) 建立物理连续内存
2. `pwritev/preadv` 与 `mach_vm_map(VM_FLAGS_OVERWRITE)` 竞态 → 物理越界读写
3. 喷射 ICMPv6 socket，破坏 `in6p_icmp6filt` 指针 → 稳定内核读写
4. 沿 `socket → so_proto → pr_input` 走链定位内核基址 + KASLR slide

## 通杀策略（版本无关化）

完全无视版本是不存在的——偏移随内核变化。本 kit 的通杀方案是
**运行时自动识别内核版本、自动选择偏移表**（`kexploit/main.m` 的 `init_offsets()`）：

| 内核 | Darwin | 偏移表 | 验证状态 |
| --- | --- | --- | --- |
| iOS 15.x | 21 | `OFF_IOS15` | 已验证（Kev1nLevin 分析） |
| iOS 16 / 17 | 22 / 23 | `OFF_IOS1617` | **未验证**（估算，套用 15.x 布局） |
| iOS 18.0–18.7 | 24 | `OFF_IOS184` | ✅ 已验证（iPhone 15 Pro / A17 Pro） |
| iOS 26.x | 25 | `OFF_IOS26` | **未验证**（估算，套用 18.4 布局） |
| 未知内核 | 其他 | 回落 `OFF_IOS184` | 打印警告 |

跑到未验证版本时 kexploit 会显式打印
`offsets UNVERIFIED for this version`——上真机前拿该版本 kernelcache 核对即可。
A18 设备（iPhone 17 系列）走 `pe_v1` 的 A18 分支（上游 `pe_v2` 未实现）。

## 偏移表（iOS 18.4 / iPhone 15 Pro，已验证）

| Define | iOS 18.4 |
| --- | --- |
| `OFFSET_PCB_SOCKET` | `0x40` |
| `OFFSET_SOCKET_SO_COUNT` | `0x254` |
| `OFFSET_ICMP6FILT` | `0x138` |
| `OFFSET_SO_PROTO` | `0x20` |
| `OFFSET_PR_INPUT` | `0x20` |
| `OFFSET_INP_GENCNT` | `0x78` |

其他设备/版本需按 kernelcache 重测（`OFFSET_ICMP6FILT` 在 iOS 15.x 是 `0x150`）。

## 构建

### 方式 A：GitHub Actions（无 Mac 推荐，免费）

1. 把本仓库推到你的 GitHub（或网页上传这些文件）
2. Actions 页签 → `build-kexploit` → Run workflow
3. 跑完在 Artifacts 下载 `kexploit-arm64-signed`（已用 ldid 签好 entitlements）

工作流文件已备好：`.github/workflows/build.yml`（macos-14 runner，
自动 `make kexploit` + `ldid` 签名 + 校验签名 + 传 artifact）。

### 方式 B：本地 macOS

```bash
brew install ldid
make kexploit SDK=iphoneos
ldid -Skexploit/entitlements.plist build/kexploit
```

## 关键限制（上游已声明）

- **未在真机测试**：需要一个能带私有 entitlements 的部署方式（原版仓库原话：
  "No known method exists for stock iOS 18.4"）——参考 [rooootdev/lara](https://github.com/rooootdev/lara)
  （基于同一 kexploit 的工具箱，声称支持 iOS 17.0–18.7.1 / 26.0.x，排除 M5 与 A19）。
- **A18 设备（iPhone17,*）路径 `pe_v2()` 未实现**（上游 TODO）。
- 这**不是越狱**：拿到内核读写后，完整越狱还需要 PPL/AMFI/CoreTrust 绕过。
  我们的形态是 kexploit 内核读写 + JS 后门注入 + C2，不必做持久化越狱。

## 致谢与来源

- 内核利用: [opa334/darksword-kexploit](https://github.com/opa334/darksword-kexploit)
- iOS 18.4 偏移: [Kev1nLevin/darksword-kexploit-ios18](https://github.com/Kev1nLevin/darksword-kexploit-ios18)
- 链路背景: [Google GTIG 分析](https://cloud.google.com/blog/topics/threat-intelligence/darksword-ios-exploit-chain)
