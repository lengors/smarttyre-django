const tooltipList = [];

window.onload = function () {
    const tooltips = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]')
    );
    tooltipList.push(
        ...tooltips.map((tooltip) => new bootstrap.Tooltip(tooltip))
    );
};
