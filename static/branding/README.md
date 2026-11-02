# Deployment logo

Place the deployment's logo at `static/branding/site-logo.png`. The default
`BRAND_LOGO_URL` points to that asset. The image itself is intentionally ignored
by Git so each local deployment can provide its own branding without changing
the application code.

The image is cropped to its visible mark before use. Keep the source file's
aspect ratio; the application contains it in the available logo area and falls
back to the `MT` mark if the configured image is missing or cannot be loaded.

The logo is included in Docker images when it is present in the build context,
because `collectstatic` runs during the image build. Rebuild deployment images
after changing the logo. Alternatively, set `BRAND_LOGO_URL` to an externally
served image URL.
