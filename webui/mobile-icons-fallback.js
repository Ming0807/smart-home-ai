(function () {
  if (window.lucide?.createIcons) {
    return;
  }

  const DEFAULT_ICON = '<circle cx="12" cy="12" r="8"/><path d="M12 8v8M8 12h8"/>';
  const ICONS = {
    activity: '<path d="M3 12h4l2-7 4 14 2-7h6"/>',
    "arrow-left": '<path d="M19 12H5"/><path d="M12 19l-7-7 7-7"/>',
    "audio-lines": '<path d="M4 12v0"/><path d="M8 7v10"/><path d="M12 4v16"/><path d="M16 7v10"/><path d="M20 12v0"/>',
    bell: '<path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 7h18s-3 0-3-7"/><path d="M10 20h4"/>',
    box: '<path d="M4 7l8-4 8 4-8 4-8-4z"/><path d="M4 7v10l8 4 8-4V7"/><path d="M12 11v10"/>',
    boxes: '<path d="M7 7l5-3 5 3-5 3-5-3z"/><path d="M4 13l5-3 5 3-5 3-5-3z"/><path d="M14 13l5-3 5 3-5 3-5-3z"/>',
    brain: '<path d="M8 6a4 4 0 0 0-2 7 4 4 0 0 0 3 7"/><path d="M16 6a4 4 0 0 1 2 7 4 4 0 0 1-3 7"/><path d="M12 4v18"/>',
    chevron: '<path d="M9 18l6-6-6-6"/>',
    "chevron-right": '<path d="M9 18l6-6-6-6"/>',
    cpu: '<rect x="7" y="7" width="10" height="10" rx="1"/><path d="M9 1v4M15 1v4M9 19v4M15 19v4M1 9h4M1 15h4M19 9h4M19 15h4"/>',
    download: '<path d="M12 3v12"/><path d="M7 10l5 5 5-5"/><path d="M4 20h16"/>',
    droplets: '<path d="M7 4c-3 4-4 6-4 8a4 4 0 0 0 8 0c0-2-1-4-4-8z"/><path d="M17 4c-3 4-4 6-4 8a4 4 0 0 0 8 0c0-2-1-4-4-8z"/>',
    fan: '<path d="M12 12m-2 0a2 2 0 1 0 4 0 2 2 0 1 0-4 0"/><path d="M12 10c1-5 5-6 7-3 1 3-2 5-5 5"/><path d="M10 13c-5 1-7-2-5-5 2-3 6-1 7 2"/><path d="M14 13c3 4 1 7-3 7-3 0-3-4-1-7"/>',
    gauge: '<path d="M4 15a8 8 0 0 1 16 0"/><path d="M12 15l4-4"/><path d="M4 19h16"/>',
    home: '<path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
    leaf: '<path d="M5 19c9 0 14-5 14-14-9 0-14 5-14 14z"/><path d="M5 19l8-8"/>',
    lightbulb: '<path d="M9 18h6"/><path d="M10 22h4"/><path d="M8 14a6 6 0 1 1 8 0c-1 1-1 2-1 3H9c0-1 0-2-1-3z"/>',
    list: '<path d="M8 6h13M8 12h13M8 18h13"/><path d="M3 6h.01M3 12h.01M3 18h.01"/>',
    "layout-grid": '<rect x="4" y="4" width="7" height="7"/><rect x="13" y="4" width="7" height="7"/><rect x="4" y="13" width="7" height="7"/><rect x="13" y="13" width="7" height="7"/>',
    "lock-keyhole": '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/><path d="M12 14v3"/>',
    menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
    message: '<path d="M4 5h16v11H8l-4 4V5z"/>',
    "message-circle": '<path d="M21 11.5a8.5 8.5 0 0 1-12.8 7.4L3 20l1.1-5.1A8.5 8.5 0 1 1 21 11.5z"/>',
    "messages-square": '<path d="M4 5h12v9H8l-4 4V5z"/><path d="M10 18h6l4 4V9h-3"/>',
    mic: '<path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3z"/><path d="M5 11a7 7 0 0 0 14 0"/><path d="M12 18v4"/>',
    "mic-vocal": '<path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3z"/><path d="M4 12c1 5 4 8 8 8s7-3 8-8"/><path d="M3 6h2M19 6h2"/>',
    "monitor-smartphone": '<rect x="3" y="4" width="13" height="10" rx="1"/><path d="M7 20h7"/><path d="M10 14v6"/><rect x="17" y="10" width="5" height="10" rx="1"/>',
    plug: '<path d="M8 2v6M16 2v6"/><path d="M6 8h12v5a6 6 0 0 1-12 0V8z"/><path d="M12 19v3"/>',
    radar: '<path d="M12 12m-2 0a2 2 0 1 0 4 0 2 2 0 1 0-4 0"/><path d="M5 19a10 10 0 1 1 14 0"/><path d="M8 16a5 5 0 1 1 8 0"/>',
    "radio-tower": '<path d="M12 12v9"/><path d="M9 21h6"/><path d="M8 8a4 4 0 0 1 8 0"/><path d="M5 5a8 8 0 0 1 14 0"/><path d="M2 2a12 12 0 0 1 20 0"/>',
    router: '<rect x="4" y="12" width="16" height="8" rx="1"/><path d="M8 16h.01M12 16h.01"/><path d="M12 8a4 4 0 0 1 4 4"/><path d="M12 4a8 8 0 0 1 8 8"/>',
    send: '<path d="M21 3L10 14"/><path d="M21 3l-7 20-4-9-9-4 20-7z"/>',
    settings: '<path d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z"/><path d="M4 12h2M18 12h2M12 4v2M12 18v2M6 6l1.5 1.5M16.5 16.5L18 18M18 6l-1.5 1.5M7.5 16.5L6 18"/>',
    "shield-alert": '<path d="M12 3l8 4v5c0 5-3 8-8 10-5-2-8-5-8-10V7l8-4z"/><path d="M12 8v5M12 17h.01"/>',
    smartphone: '<rect x="7" y="2" width="10" height="20" rx="2"/><path d="M11 18h2"/>',
    sparkles: '<path d="M12 3l1.5 5L18 10l-4.5 2L12 17l-1.5-5L6 10l4.5-2L12 3z"/><path d="M5 15l.7 2.3L8 18l-2.3.7L5 21l-.7-2.3L2 18l2.3-.7L5 15z"/>',
    thermometer: '<path d="M10 14.5V5a2 2 0 0 1 4 0v9.5a4 4 0 1 1-4 0z"/>',
  };

  function buildSvg(name, source) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    const className = source.getAttribute("class");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("fill", "none");
    svg.setAttribute("stroke", "currentColor");
    svg.setAttribute("stroke-width", "2");
    svg.setAttribute("stroke-linecap", "round");
    svg.setAttribute("stroke-linejoin", "round");
    svg.setAttribute("aria-hidden", source.getAttribute("aria-hidden") || "true");
    if (className) {
      svg.setAttribute("class", className);
    }
    svg.innerHTML = ICONS[name] || DEFAULT_ICON;
    return svg;
  }

  window.lucide = {
    createIcons() {
      document.querySelectorAll("i[data-lucide]").forEach((icon) => {
        icon.replaceWith(buildSvg(icon.getAttribute("data-lucide") || "", icon));
      });
    },
  };
})();
