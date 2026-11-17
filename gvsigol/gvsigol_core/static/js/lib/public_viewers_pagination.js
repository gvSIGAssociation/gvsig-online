(function (global) {
	function fold(value) {
		return (value || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
	}

	function paginateCards(gridId, navId, sectionId, perPage) {
		var grid = document.getElementById(gridId);
		var nav = document.getElementById(navId);
		if (!grid || !nav) return;

		var cards = Array.prototype.slice.call(grid.querySelectorAll('.pub-project-card'));
		var search = document.getElementById(gridId + '-search');
		var empty = document.getElementById(gridId + '-empty');
		perPage = perPage || 8;
		if (!search && Math.ceil(cards.length / perPage) <= 1) return;

		var filtered = cards.slice();
		var current = 0;
		var pages = 1;

		function showPage(page) {
			current = page;
			pages = Math.ceil(filtered.length / perPage) || 1;
			cards.forEach(function (card) { card.style.display = 'none'; });
			filtered.forEach(function (card, i) {
				card.style.display = (i >= page * perPage && i < (page + 1) * perPage) ? '' : 'none';
			});
			if (empty) empty.hidden = filtered.length !== 0;
			renderPagination();
		}

		function btn(label, page, disabled, active) {
			var a = document.createElement('a');
			a.href = '#' + sectionId;
			a.innerHTML = label;
			if (disabled) { a.className = 'pub-page-btn disabled'; a.setAttribute('aria-disabled', 'true'); }
			else if (active) { a.className = 'pub-page-btn active'; a.setAttribute('aria-current', 'page'); }
			else { a.className = 'pub-page-btn'; }
			if (!disabled && !active) {
				a.addEventListener('click', function (e) {
					e.preventDefault();
					showPage(page);
					var section = document.getElementById(sectionId);
					if (section) {
						section.scrollIntoView({ behavior: 'smooth', block: 'start' });
					}
				});
			} else {
				a.addEventListener('click', function (e) { e.preventDefault(); });
			}
			return a;
		}

		function renderPagination() {
			nav.innerHTML = '';
			if (pages <= 1) return;
			var ul = document.createElement('ul');
			ul.className = 'pub-page-list';

			var liPrev = document.createElement('li');
			liPrev.appendChild(btn('&laquo;', current - 1, current === 0, false));
			ul.appendChild(liPrev);

			for (var p = 0; p < pages; p++) {
				var li = document.createElement('li');
				li.appendChild(btn(p + 1, p, false, p === current));
				ul.appendChild(li);
			}

			var liNext = document.createElement('li');
			liNext.appendChild(btn('&raquo;', current + 1, current === pages - 1, false));
			ul.appendChild(liNext);

			nav.appendChild(ul);
		}

		if (search) {
			search.addEventListener('input', function () {
				var query = fold(search.value.trim());
				filtered = query ? cards.filter(function (card) {
					return fold(card.textContent).indexOf(query) !== -1;
				}) : cards.slice();
				showPage(0);
			});
		}

		showPage(0);
	}

	global.gvsigolPaginateCards = paginateCards;
	if (!global._gvsigolPubViewersPaginated) {
		global._gvsigolPubViewersPaginated = true;
		paginateCards('pub-projects-grid', 'pub-pagination', 'public-viewers');
	}
}(typeof window !== 'undefined' ? window : this));
