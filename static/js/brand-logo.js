"""Enable the supplied brand logo while retaining the text mark fallback."""

document.querySelectorAll(".brand-logo").forEach((image) => {
    const mark = image.closest(".brand-mark");
    if (!mark) return;

    const useImage = () => {
        if (image.naturalWidth > 0) {
            mark.classList.add("has-logo");
            mark.classList.remove("logo-error");
        } else {
            mark.classList.remove("has-logo");
            mark.classList.add("logo-error");
        }
    };

    image.addEventListener("load", useImage, { once: true });
    image.addEventListener("error", useImage, { once: true });
    if (image.complete) useImage();
});
