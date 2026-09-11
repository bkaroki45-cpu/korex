function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");

    sidebar.classList.toggle("open");
}

document.addEventListener("DOMContentLoaded", () => {
    const viewport = document.querySelector(".banner-viewport");
    const track = document.querySelector(".banner-track");
    const firstSet = document.querySelector(".banner-set");
    const secondSet = track?.querySelector('.banner-set[aria-hidden="true"]');
    if (!viewport || !track || !firstSet || !secondSet) return;

    const allSlides = [...firstSet.children, ...secondSet.children];
    const slideCount = firstSet.children.length;
    if (slideCount < 2) return;
    let position = 0;
    let step = 0;
    let activeIndex = 0;
    let resetTimer;
    const dots = [...document.querySelectorAll(".guide-dots button")];
    const updateDots = () => dots.forEach((dot, index) => dot.classList.toggle("active", index === activeIndex));

    const layout = () => {
        const cardsVisible = window.innerWidth <= 700 ? 1 : (window.innerWidth <= 1100 ? 3 : 4);
        const gap = window.innerWidth <= 700 ? 12 : 16;
        const padding = window.innerWidth <= 700 ? 18 : 32;
        const cardWidth = Math.floor((viewport.clientWidth - padding - gap * (cardsVisible - 1)) / cardsVisible);
        const cardHeight = Math.round(cardWidth * 721 / 490);
        step = cardWidth + gap;
        track.style.cssText = "display:flex;width:max-content;animation:none;transform:translateX(" + position + "px);transition:transform 650ms cubic-bezier(.22,.61,.36,1)";
        [firstSet, secondSet].forEach((set) => {
            set.style.cssText = "display:flex;flex:0 0 auto;gap:" + gap + "px;padding:" + (window.innerWidth <= 700 ? "9px" : "12px 16px") + "px";
        });
        allSlides.forEach((slide) => {
            slide.style.cssText = "display:block;flex:0 0 auto;width:" + cardWidth + "px;height:" + cardHeight + "px";
        });
    };

    layout();
    window.addEventListener("resize", () => { position = 0; activeIndex = 0; layout(); updateDots(); });
    const slide = (direction = 1, chosenIndex = null) => {
        window.clearTimeout(resetTimer);
        activeIndex = chosenIndex === null ? (activeIndex + direction + slideCount) % slideCount : chosenIndex;
        position = -step * activeIndex;
        track.style.transition = "transform 650ms cubic-bezier(.22,.61,.36,1)";
        track.style.transform = "translateX(" + position + "px)";
        updateDots();
    };
    document.querySelector("[data-guide-prev]")?.addEventListener("click", () => slide(-1));
    document.querySelector("[data-guide-next]")?.addEventListener("click", () => slide(1));
    dots.forEach((dot, index) => dot.addEventListener("click", () => slide(1, index)));
    let touchStart = 0;
    viewport.addEventListener("touchstart", (event) => { touchStart = event.changedTouches[0].clientX; }, {passive: true});
    viewport.addEventListener("touchend", (event) => { const distance = event.changedTouches[0].clientX - touchStart; if (Math.abs(distance) > 35) slide(distance < 0 ? 1 : -1); }, {passive: true});
    window.setInterval(() => slide(1), 3000);
});
