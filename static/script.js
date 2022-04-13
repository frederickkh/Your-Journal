function toggleDark() {
    var body = document.body;
    var table = document.getElementById("history");
    var card = document.getElementsByClassName("card");
    var pin = document.getElementById("pin");
    var newcancel = document.getElementById("newcancel");
    var editcancel = document.getElementById("editcancel");
    var home = document.getElementById("home");

    body.classList.toggle("darkmode");
    // table.classList.toggle("darkmode");
    card.classList.toggle("card-dark");
    pin.classList.toggle("btn-dark");
    // newcancel.classList.toggle("btn-dark");
    // editcancel.classList.toggle("btn-dark");
    // home.classList.toggle("btn-dark");
}
