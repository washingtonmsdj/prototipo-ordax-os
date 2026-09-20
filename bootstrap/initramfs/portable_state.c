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
    fputs("usage: ordax-portable-state <state-root> <current|known-good|candidate>\n", stderr);
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

int main(int argc, char **argv) {
    if (argc != 3 || !valid_slot(argv[2])) {
        die_usage();
    }

    int root = safe_root(argv[1]);
    if (root < 0) {
        fprintf(stderr, "ordax-portable-state: unsafe state root: %s\n", strerror(errno));
        return EXIT_INVALID;
    }
    int ordax = safe_dir_at(root, "ordax");
    close(root);
    if (ordax < 0) {
        if (errno == ENOENT) {
            return EXIT_ABSENT;
        }
        fprintf(stderr, "ordax-portable-state: unsafe ordax state directory\n");
        return EXIT_INVALID;
    }
    int release = safe_dir_at(ordax, "portable-release");
    close(ordax);
    if (release < 0) {
        if (errno == ENOENT) {
            return EXIT_ABSENT;
        }
        fprintf(stderr, "ordax-portable-state: unsafe portable release state directory\n");
        return EXIT_INVALID;
    }

    char commit[41];
    int rc = read_commit(release, argv[2], commit);
    close(release);
    if (rc != 0) {
        if (rc == EXIT_INVALID) {
            fprintf(stderr, "ordax-portable-state: invalid %s identity\n", argv[2]);
        }
        return rc;
    }

    if (write_all(commit, 40) != 0 || write_all("\n", 1) != 0) {
        fprintf(stderr, "ordax-portable-state: cannot write result\n");
        return EXIT_INVALID;
    }
    return 0;
}
