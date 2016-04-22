/*
 * TODO Layer Tree Custom
 * -----------------------
 *
 * @type plugin
 * @usage $("#layer-tree").layerTree( options );
 */
(function ($) {

	'use strict';

	$.fn.layerTree = function (options) {
		// Render options
		var settings = $.extend({
			//When the user checks the input
			onCheck: function (ele) {
				return ele;
			},
			//When the user unchecks the input
			onUncheck: function (ele) {
				return ele;
			}
		}, options);

		return this.each(function () {

			$('input', this).on('change', function () {
				var ele = $(this).parents("li").first();
				ele.toggleClass("done");
				if ($('input', ele).is(":checked")) {
					settings.onCheck.call(ele);
				} else {
					settings.onUncheck.call(ele);
				}
			});
		});
	};
}(jQuery));