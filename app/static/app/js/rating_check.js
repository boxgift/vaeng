function get_all_input_for_rating() {
    return document.querySelectorAll('div.rating-area input');
}

function get_all_rating() {
    let rating = 0;
    let checkboxes = get_all_input_for_rating();
    checkboxes.forEach((checkbox) => checkbox.checked ? rating += parseInt(checkbox.value) : null)
    return rating
}

function get_base_rating() {
    let rating_area = document.getElementsByClassName('rating-area');
    let length = rating_area.length;
    let rating = get_all_rating() / length
    return rating.toFixed(1);
}

function set_base_rating() {
    let base_rating = document.getElementById('base_rating');
    base_rating.innerText = get_base_rating();
}
set_base_rating()
get_all_input_for_rating().forEach((input) => input.addEventListener('change', set_base_rating))