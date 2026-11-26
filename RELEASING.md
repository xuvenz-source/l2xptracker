# Maintainer release checklist

1. The repository is https://github.com/xuvenz-source/l2xptracker and is already public. Push the files from this folder (including hidden `.github`). Do not upload personal settings, logs or databases.
2. Check that the Actions test workflow passes. Pushes to main automatically build after successful tests. To rebuild manually, under Actions choose **Windows tests and portable build**, then **Run workflow** on the trusted main branch. The Windows runner installs the pinned Chocolatey Tesseract distribution and invokes the existing builder and frozen-app self-test. The v0.19 Windows build passed; validate the new updater workflow before sharing.
3. Download the workflow artifact, extract its outer archive, and verify the inner portable ZIP on a clean Windows x64 PC. Test HUD, session saving, pause/resume, and OCR with server permission. Check SHA-256 and compare actual XP/Adena with recorded values.
4. Check the actual bundled dependency notices and meet all redistribution requirements (including any applicable source-offer requirements); choose a source license separately. Get server approval before recommending use on Reborn. The application remains unsigned.
5. The workflow creates a draft GitHub Release tagged `v0.24` from the tested commit, with the portable ZIP and `.sha256` file. Verify both assets and edit release notes. Publish only after review. Public release assets can then be downloaded without a GitHub account.
6. For later releases, update VERSION in version.py, README.md and READ ME - Portable.txt to match the new tag. Repeat the checks. Never commit generated ZIPs or personal data to source control.

The workflow deliberately does not publish releases automatically. The release is an owner decision after smoke tests, license review, and clean-PC testing. Future automation can create draft releases after builds once this process is validated.

The updater ignores drafts and prereleases. The draft job does not overwrite an existing release; bump the version or deliberately replace a draft after review. Test an upgrade on Windows before relying on automatic installation. Do not publish until the checks above are complete.
