const songs = [

];

const searchInput = document.querySelector('.search-input');
const suggestionsBox = document.querySelector('.suggestions');

searchInput.addEventListener('keyup', function() {
    const input = searchInput.value;
    suggestionsBox.innerHTML = '';
    const suggestions =
})