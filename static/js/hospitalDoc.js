document.addEventListener("DOMContentLoaded", function () {

  function loadDoctors(url) {
    fetch(url, {
      headers: {
        "X-Requested-With": "XMLHttpRequest"
      }
    })
    .then(response => response.json())
    .then(data => {
      document.getElementById("doctor-list").innerHTML = data.html;
      window.history.pushState({}, "", url); // update URL
    });
  }

  // 🔹 Filter click
  document.querySelectorAll(".filter-link").forEach(link => {
    link.addEventListener("click", function(e) {
      e.preventDefault();
      loadDoctors(this.href);
    });
  });

  // 🔹 Pagination click
document.querySelectorAll(".pagination-link").forEach(link => {
  link.addEventListener("click", function(e) {
    e.preventDefault();
    window.location.href = this.href;  // ✅ full reload
  });
});

});

{/* Top button  */}
document.getElementById("sort-select").addEventListener("change", function() {
  const selectedSort = this.value;

  const url = new URL(window.location.href);

  if (selectedSort) {
    url.searchParams.set("sort", selectedSort);
  } else {
    url.searchParams.delete("sort");
  }

  // keep specialty filter
  const specialty = url.searchParams.get("specialty");

  // reset page
  url.searchParams.delete("page");

  // ✅ AJAX load
  fetch(url.toString(), {
    headers: {
      "X-Requested-With": "XMLHttpRequest"
    }
  })
  .then(res => res.json())
  .then(data => {
    document.getElementById("doctor-list").innerHTML = data.html;
    window.history.pushState({}, "", url);
  });
});
