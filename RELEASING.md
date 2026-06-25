# Releasing yt-tutor to PyPI

The package is publish-ready: `python -m build` produces a valid sdist and wheel, and
`twine check` passes. Publishing uses **PyPI Trusted Publishing** (OIDC), so there is no API
token to manage. The workflow is [`.github/workflows/publish.yml`](.github/workflows/publish.yml).

The name `yt-tutor` is available on PyPI as of this writing. The first publish claims it.

## One-time setup (you do this once, on PyPI)

1. Create a PyPI account at <https://pypi.org> if you do not have one.
2. Add a **pending trusted publisher** so the very first upload can create the project:
   <https://pypi.org/manage/account/publishing/>. Fill in exactly:
   - PyPI Project Name: `yt-tutor`
   - Owner: `josuesto`
   - Repository name: `yt-tutor`
   - Workflow name: `publish.yml`
   - Environment name: `pypi`

That binds GitHub Actions in this repo (the `pypi` environment) to publish `yt-tutor` with no
secret.

## Publish the first release (0.1.0)

The `v0.1.0` GitHub Release already exists, created before the publish workflow, so it will not
auto-trigger. Publish it manually once:

- GitHub → **Actions** → **Publish to PyPI** → **Run workflow** (on `main`).

It builds, runs `twine check`, and uploads via Trusted Publishing. Then:

- Confirm the page at <https://pypi.org/project/yt-tutor/>.
- Flip the install instructions to PyPI: in `README.md` and `SKILL.md`, change the
  `pipx install "git+https://github.com/josuesto/yt-tutor"` lines to `pip install yt-tutor`
  (keep the from-source path for development), and drop the "not on PyPI yet" notes.

## Future releases

1. Bump `version` in `pyproject.toml` (semver).
2. Move `CHANGELOG.md`'s `[Unreleased]` items under a new `[X.Y.Z]` section with the date.
3. Commit, then tag and release:
   ```bash
   git tag -a vX.Y.Z -m "yt-tutor vX.Y.Z"
   git push origin vX.Y.Z
   gh release create vX.Y.Z --title "yt-tutor vX.Y.Z" --notes "..."
   ```
   Publishing the GitHub Release triggers the workflow, which builds and uploads automatically.

## Manual fallback (if you prefer a token)

```bash
python -m build
python -m twine upload dist/*    # prompts for an API token from https://pypi.org/manage/account/token/
```

## Test it first (optional)

To rehearse without touching the real index, add a TestPyPI trusted publisher the same way and
publish there (<https://test.pypi.org>), then `pip install -i https://test.pypi.org/simple/ yt-tutor`.
