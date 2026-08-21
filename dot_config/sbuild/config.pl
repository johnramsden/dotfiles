$chroot_mode = 'unshare';
$unshare_mmdebstrap_keep_tarball = 1;

$unshare_tmpdir_template = '/var/tmp/tmp.sbuild.XXXXXXXXXX';

# Must stay 1 (sbuild's default) when building from an unpacked source tree.
# With 0, sbuild skips `debian/rules clean`, so packages relying on
# debian/clean to remove files before dpkg-source compares the tree against
# the orig tarball fail with "unexpected upstream changes" (e.g. ceph).
$clean_source = 1;
$run_lintian = 0;
