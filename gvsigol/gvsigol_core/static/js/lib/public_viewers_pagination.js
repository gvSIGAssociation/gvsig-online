(function (global) {
	function paginateCards(gridId, navId, sectionId, perPage) {
		var grid = document.getElementById(gridId);
		var nav = document.getElementById(navId);
		if (!grid || !nav) return;

		var cards = Array.prototype.slice.call(grid.querySelectorAll('.pub-project-card'));
		perPage = perPage || 8;
		var total = cards.length;
		var pages = Math.ceil(total / perPage);
		if (pages <= 1) return;

		var current = 0;

		function showPage(page) {
			current = page;
			cards.forEach(function (card, i) {
				card.style.display = (i >= page * perPage && i < (page + 1) * perPage) ? '' : 'none';
			});
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

		showPage(0);
	}

	global.gvsigolPaginateCards = paginateCards;
	if (!global._gvsigolPubViewersPaginated) {
		global._gvsigolPubViewersPaginated = true;
		paginateCards('pub-projects-grid', 'pub-pagination', 'public-viewers');
	}
}(typeof window !== 'undefined' ? window : this));
