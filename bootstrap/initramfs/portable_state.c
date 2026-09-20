#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

enum {
    EXIT_USAGE = 2,
    EXIT_ABSENT = 3,
    EXIT_INVALID = 4,
};

static void die_usage(void) {
    fputs(
        "usage:\n"
        "  ordax-portable-state <state-root> <current|known-good|candidate>\n"
        "  ordax-portable-state select <state-root> <portable-root>\n",
        stderr
    );
    exit(EXIT_USAGE);
}

static int safe_dir_at(int parent, const char *name) {
    int fd = openat(parent, name, O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -1;
    }
    struct stat st;
    if (fstat(fd, &st) != 0 || !S_ISDIR(st.st_mode)) {
        close(fd);
        errno = ENOTDIR;
        return -1;
    }
    return fd;
}

static int safe_root(const char *path) {
    int fd = open(path, O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -1;
    }
    struct stat st;
    if (fstat(fd, &st) != 0 || !S_ISDIR(st.st_mode)) {
        close(fd);
        errno = ENOTDIR;
        return -1;
    }
    return fd;
}

static int valid_slot(const char *slot) {
    return strcmp(slot, "current") == 0 ||
           strcmp(slot, "known-good") == 0 ||
           strcmp(slot, "candidate") == 0;
}

static int read_commit(int parent, const char *slot, char out[41]) {
    int fd = openat(parent, slot, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return errno == ENOENT ? EXIT_ABSENT : EXIT_INVALID;
    }

    struct stat st;
    if (fstat(fd, &st) != 0 ||
        !S_ISREG(st.st_mode) ||
        st.st_nlink != 1 ||
        st.st_size < 40 ||
        st.st_size > 41) {
        close(fd);
        return EXIT_INVALID;
    }

    char buffer[42] = {0};
    ssize_t n = read(fd, buffer, sizeof(buffer));
    if (n < 0) {
        close(fd);
        return EXIT_INVALID;
    }
    char extra;
    ssize_t extra_n = read(fd, &extra, 1);
    close(fd);
    if (extra_n != 0) {
        return EXIT_INVALID;
    }
    if (n != 40 && n != 41) {
        return EXIT_INVALID;
    }
    if (n == 41 && buffer[40] != '\n') {
        return EXIT_INVALID;
    }
    for (int i = 0; i < 40; i++) {
        const char ch = buffer[i];
        if (!((ch >= '0' && ch <= '9') || (ch >= 'a' && ch <= 'f'))) {
            return EXIT_INVALID;
        }
        out[i] = ch;
    }
    out[40] = '\0';
    return 0;
}

static int safe_regular_at(int parent, const char *name, off_t minimum_size) {
    int fd = openat(parent, name, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
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

static int erofs_magic_ok(int fd) {
    unsigned char magic[4];
    ssize_t n = pread(fd, magic, sizeof(magic), 1024);
    return n == 4 &&
           magic[0] == 0xe2 &&
           magic[1] == 0xe1 &&
           magic[2] == 0xf5 &&
           magic[3] == 0xe0;
}

static int release_materialized_safely(int releases, const char *commit) {
    int release = safe_dir_at(releases, commit);
    if (release < 0) {
        return 0;
    }

    int image = safe_regular_at(release, "system.erofs", 4096);
    int manifest = safe_regular_at(release, "release-manifest.json", 2);
    int envelope = safe_regular_at(release, "release-envelope.json", 2);
    int ok = image >= 0 &&
             manifest >= 0 &&
             envelope >= 0 &&
             erofs_magic_ok(image);

    if (image >= 0) {
        close(image);
    }
    if (manifest >= 0) {
        close(manifest);
    }
    if (envelope >= 0) {
        close(envelope);
    }
    close(release);
    return ok;
}

static int open_release_state_root(const char *state_root) {
    int root = safe_root(state_root);
    if (root < 0) {
        return -1;
    }
    int ordax = safe_dir_at(root, "ordax");
    close(root);
    if (ordax < 0) {
        return -1;
    }
    int release = safe_dir_at(ordax, "portable-release");
    close(ordax);
    return release;
}

static int open_materialized_releases(const char *portable_root) {
    int root = safe_root(portable_root);
    if (root < 0) {
        return -1;
    }
    int releases = safe_dir_at(root, "releases");
    close(root);
    return releases;
}

static int write_all(const char *value, size_t length) {
    while (length > 0) {
        ssize_t n = write(STDOUT_FILENO, value, length);
        if (n < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        value += (size_t)n;
        length -= (size_t)n;
    }
    return 0;
}

static int print_commit(const char *commit) {
    return write_all(commit, 40) == 0 && write_all("\n", 1) == 0 ? 0 : -1;
}

static int read_slot_command(const char *state_root, const char *slot) {
    if (!valid_slot(slot)) {
        return EXIT_USAGE;
    }
    int release = open_release_state_root(state_root);
    if (release < 0) {
        if (errno == ENOENT) {
            return EXIT_ABSENT;
        }
        fputs("ordax-portable-state: unsafe portable release state root\n", stderr);
        return EXIT_INVALID;
    }

    char commit[41];
    int rc = read_commit(release, slot, commit);
    close(release);
    if (rc != 0) {
        if (rc == EXIT_INVALID) {
            fprintf(stderr, "ordax-portable-state: invalid %s identity\n", slot);
        }
        return rc;
    }
    if (print_commit(commit) != 0) {
        fputs("ordax-portable-state: cannot write result\n", stderr);
        return EXIT_INVALID;
    }
    return 0;
}

static int select_command(const char *state_root, const char *portable_root) {
    int release_state = open_release_state_root(state_root);
    if (release_state < 0) {
        if (errno == ENOENT) {
            return EXIT_ABSENT;
        }
        fputs("ordax-portable-state: unsafe portable release state root\n", stderr);
        return EXIT_INVALID;
    }

    int releases = open_materialized_releases(portable_root);
    if (releases < 0) {
        close(release_state);
        if (errno == ENOENT) {
            return EXIT_ABSENT;
        }
        fputs("ordax-portable-state: unsafe materialized releases root\n", stderr);
        return EXIT_INVALID;
    }

    const char *slots[] = {"current", "known-good"};
    char commit[41];
    for (size_t index = 0; index < sizeof(slots) / sizeof(slots[0]); index++) {
        const char *slot = slots[index];
        int rc = read_commit(release_state, slot, commit);
        if (rc != 0) {
            continue;
        }
        if (!release_materialized_safely(releases, commit)) {
            continue;
        }

        if (write_all(slot, strlen(slot)) != 0 ||
            write_all(" ", 1) != 0 ||
            print_commit(commit) != 0) {
            close(releases);
            close(release_state);
            fputs("ordax-portable-state: cannot write selection\n", stderr);
            return EXIT_INVALID;
        }
        close(releases);
        close(release_state);
        return 0;
    }

    close(releases);
    close(release_state);
    fputs("ordax-portable-state: no safely materialized current or known-good release\n", stderr);
    return EXIT_ABSENT;
}

int main(int argc, char **argv) {
    if (argc == 4 && strcmp(argv[1], "select") == 0) {
        return select_command(argv[2], argv[3]);
    }
    if (argc == 3 && valid_slot(argv[2])) {
        return read_slot_command(argv[1], argv[2]);
    }
    die_usage();
    return EXIT_USAGE;
}
