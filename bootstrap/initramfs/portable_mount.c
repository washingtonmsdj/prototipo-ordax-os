#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/loop.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

enum {
    EXIT_USAGE = 2,
    EXIT_UNSAFE = 3,
    EXIT_LOOP = 4,
    EXIT_MOUNT = 5,
};

struct loop_binding {
    int control_fd;
    int loop_fd;
    int backing_fd;
    char device[64];
    int attached;
};

static void usage(void) {
    fputs(
        "usage:\n"
        "  ordax-portable-mount mount-state <state.img> <state-mount>\n"
        "  ordax-portable-mount mount-system <system.erofs> <state-mount> <release-mount> <system-mount>\n",
        stderr
    );
}

static int safe_absolute_path(const char *path) {
    if (path == NULL || path[0] != '/' || strlen(path) >= PATH_MAX) {
        return 0;
    }
    if (strchr(path, '\n') != NULL || strchr(path, '\r') != NULL) {
        return 0;
    }
    return 1;
}

static int safe_overlay_path(const char *path) {
    return safe_absolute_path(path) &&
           strchr(path, ',') == NULL &&
           strchr(path, ':') == NULL &&
           strchr(path, '\\') == NULL;
}

static int real_directory(const char *path) {
    struct stat st;
    if (!safe_absolute_path(path) || lstat(path, &st) != 0) {
        return 0;
    }
    return S_ISDIR(st.st_mode) && !S_ISLNK(st.st_mode);
}

static int open_regular(const char *path, int writable, off_t minimum_size) {
    if (!safe_absolute_path(path) || strncmp(path, "/dev/", 5) == 0) {
        errno = EINVAL;
        return -1;
    }
    int flags = (writable ? O_RDWR : O_RDONLY) | O_CLOEXEC | O_NOFOLLOW;
    int fd = open(path, flags);
    if (fd < 0) {
        return -1;
    }
    struct stat st;
    if (fstat(fd, &st) != 0 ||
        !S_ISREG(st.st_mode) ||
        st.st_nlink != 1 ||
        st.st_size < minimum_size) {
        close(fd);
        errno = EINVAL;
        return -1;
    }
    return fd;
}

static int ext4_superblock_magic_ok(int fd) {
    unsigned char magic[2];
    ssize_t n = pread(fd, magic, sizeof(magic), 1024 + 56);
    return n == 2 && magic[0] == 0x53 && magic[1] == 0xef;
}

static int erofs_superblock_magic_ok(int fd) {
    unsigned char magic[4];
    ssize_t n = pread(fd, magic, sizeof(magic), 1024);
    return n == 4 &&
           magic[0] == 0xe2 &&
           magic[1] == 0xe1 &&
           magic[2] == 0xf5 &&
           magic[3] == 0xe0;
}

static void loop_binding_init(struct loop_binding *binding) {
    memset(binding, 0, sizeof(*binding));
    binding->control_fd = -1;
    binding->loop_fd = -1;
    binding->backing_fd = -1;
}

static void loop_binding_cleanup(struct loop_binding *binding) {
    if (binding->attached && binding->loop_fd >= 0) {
        (void)ioctl(binding->loop_fd, LOOP_CLR_FD, 0);
    }
    if (binding->backing_fd >= 0) {
        close(binding->backing_fd);
    }
    if (binding->loop_fd >= 0) {
        close(binding->loop_fd);
    }
    if (binding->control_fd >= 0) {
        close(binding->control_fd);
    }
    loop_binding_init(binding);
}

static int loop_attach(
    struct loop_binding *binding,
    const char *backing_path,
    int writable,
    int verify_ext4,
    int verify_erofs
) {
    loop_binding_init(binding);
    binding->backing_fd = open_regular(
        backing_path,
        writable,
        verify_ext4 ? (off_t)(4 * 1024 * 1024) : (off_t)4096
    );
    if (binding->backing_fd < 0) {
        return -1;
    }
    if (verify_ext4 && !ext4_superblock_magic_ok(binding->backing_fd)) {
        errno = EINVAL;
        loop_binding_cleanup(binding);
        return -1;
    }
    if (verify_erofs && !erofs_superblock_magic_ok(binding->backing_fd)) {
        errno = EINVAL;
        loop_binding_cleanup(binding);
        return -1;
    }

    binding->control_fd = open("/dev/loop-control", O_RDWR | O_CLOEXEC | O_NOFOLLOW);
    if (binding->control_fd < 0) {
        loop_binding_cleanup(binding);
        return -1;
    }
    int number = ioctl(binding->control_fd, LOOP_CTL_GET_FREE);
    if (number < 0) {
        loop_binding_cleanup(binding);
        return -1;
    }
    int written = snprintf(binding->device, sizeof(binding->device), "/dev/loop%d", number);
    if (written <= 0 || (size_t)written >= sizeof(binding->device)) {
        errno = EOVERFLOW;
        loop_binding_cleanup(binding);
        return -1;
    }
    binding->loop_fd = open(
        binding->device,
        (writable ? O_RDWR : O_RDONLY) | O_CLOEXEC | O_NOFOLLOW
    );
    if (binding->loop_fd < 0) {
        loop_binding_cleanup(binding);
        return -1;
    }
    if (ioctl(binding->loop_fd, LOOP_SET_FD, binding->backing_fd) != 0) {
        loop_binding_cleanup(binding);
        return -1;
    }
    binding->attached = 1;

    struct loop_info64 info;
    memset(&info, 0, sizeof(info));
    info.lo_flags = LO_FLAGS_AUTOCLEAR;
    if (!writable) {
        info.lo_flags |= LO_FLAGS_READ_ONLY;
    }
    size_t name_len = strlen(backing_path);
    if (name_len >= sizeof(info.lo_file_name)) {
        name_len = sizeof(info.lo_file_name) - 1;
    }
    memcpy(info.lo_file_name, backing_path, name_len);
    info.lo_file_name[name_len] = '\0';

    if (ioctl(binding->loop_fd, LOOP_SET_STATUS64, &info) != 0) {
        loop_binding_cleanup(binding);
        return -1;
    }
    return 0;
}

static int mount_state(const char *state_image, const char *state_mount) {
    if (!real_directory(state_mount)) {
        fputs("ordax-portable-mount: state mountpoint is unsafe\n", stderr);
        return EXIT_UNSAFE;
    }

    struct loop_binding state;
    if (loop_attach(&state, state_image, 1, 1, 0) != 0) {
        fprintf(stderr, "ordax-portable-mount: cannot attach ext4 state image: %s\n", strerror(errno));
        return EXIT_LOOP;
    }

    unsigned long flags = MS_NODEV | MS_NOSUID;
    if (mount(state.device, state_mount, "ext4", flags, "errors=remount-ro") != 0) {
        fprintf(stderr, "ordax-portable-mount: cannot mount ext4 state: %s\n", strerror(errno));
        loop_binding_cleanup(&state);
        return EXIT_MOUNT;
    }

    state.attached = 0;
    close(state.backing_fd);
    close(state.loop_fd);
    close(state.control_fd);
    printf("ORDAX_PORTABLE_STATE_LOOP=%s\n", state.device);
    return 0;
}

static int safe_child_directory(const char *root, const char *child, char output[PATH_MAX]) {
    if (!safe_overlay_path(root) || strchr(child, '/') != NULL) {
        return 0;
    }
    int written = snprintf(output, PATH_MAX, "%s/%s", root, child);
    if (written <= 0 || written >= PATH_MAX) {
        return 0;
    }
    return real_directory(output);
}

static int safe_entrypoint(const char *system_root) {
    char path[PATH_MAX];
    int written = snprintf(path, sizeof(path), "%s/entrypoint", system_root);
    if (written <= 0 || written >= (int)sizeof(path)) {
        return 0;
    }
    struct stat st;
    if (lstat(path, &st) != 0 ||
        !S_ISREG(st.st_mode) ||
        S_ISLNK(st.st_mode) ||
        (st.st_mode & 0111) == 0) {
        return 0;
    }
    return 1;
}

static int mount_system(
    const char *release_image,
    const char *state_mount,
    const char *release_mount,
    const char *system_mount
) {
    if (!safe_overlay_path(state_mount) ||
        !safe_overlay_path(release_mount) ||
        !safe_overlay_path(system_mount) ||
        !real_directory(state_mount) ||
        !real_directory(release_mount) ||
        !real_directory(system_mount)) {
        fputs("ordax-portable-mount: system mount path is unsafe\n", stderr);
        return EXIT_UNSAFE;
    }

    char upper[PATH_MAX];
    char work[PATH_MAX];
    if (!safe_child_directory(state_mount, "upper", upper) ||
        !safe_child_directory(state_mount, "work", work)) {
        fputs("ordax-portable-mount: ext4 state lacks safe upper/work directories\n", stderr);
        return EXIT_UNSAFE;
    }

    struct loop_binding release;
    if (loop_attach(&release, release_image, 0, 0, 1) != 0) {
        fprintf(stderr, "ordax-portable-mount: cannot attach EROFS release image: %s\n", strerror(errno));
        return EXIT_LOOP;
    }

    unsigned long release_flags = MS_RDONLY | MS_NODEV | MS_NOSUID;
    if (mount(release.device, release_mount, "erofs", release_flags, NULL) != 0) {
        fprintf(stderr, "ordax-portable-mount: cannot mount EROFS release: %s\n", strerror(errno));
        loop_binding_cleanup(&release);
        return EXIT_MOUNT;
    }

    char lower[PATH_MAX];
    if (!safe_child_directory(release_mount, "system", lower) || !safe_entrypoint(lower)) {
        fputs("ordax-portable-mount: EROFS release lacks a safe executable system/entrypoint\n", stderr);
        (void)umount2(release_mount, MNT_DETACH);
        loop_binding_cleanup(&release);
        return EXIT_UNSAFE;
    }

    char options[PATH_MAX * 3];
    int written = snprintf(
        options,
        sizeof(options),
        "lowerdir=%s,upperdir=%s,workdir=%s",
        lower,
        upper,
        work
    );
    if (written <= 0 || written >= (int)sizeof(options)) {
        fputs("ordax-portable-mount: overlay option path is too long\n", stderr);
        (void)umount2(release_mount, MNT_DETACH);
        loop_binding_cleanup(&release);
        return EXIT_UNSAFE;
    }

    if (mount("overlay", system_mount, "overlay", MS_NODEV | MS_NOSUID, options) != 0) {
        fprintf(stderr, "ordax-portable-mount: cannot mount OverlayFS system view: %s\n", strerror(errno));
        (void)umount2(release_mount, MNT_DETACH);
        loop_binding_cleanup(&release);
        return EXIT_MOUNT;
    }

    release.attached = 0;
    close(release.backing_fd);
    close(release.loop_fd);
    close(release.control_fd);
    printf("ORDAX_PORTABLE_RELEASE_LOOP=%s\n", release.device);
    printf("ORDAX_PORTABLE_SYSTEM_ROOT=%s\n", system_mount);
    return 0;
}

int main(int argc, char **argv) {
    if (argc == 4 && strcmp(argv[1], "mount-state") == 0) {
        return mount_state(argv[2], argv[3]);
    }
    if (argc == 6 && strcmp(argv[1], "mount-system") == 0) {
        return mount_system(argv[2], argv[3], argv[4], argv[5]);
    }
    usage();
    return EXIT_USAGE;
}
