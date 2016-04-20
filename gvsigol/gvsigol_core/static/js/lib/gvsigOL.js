/*! gvsigOL app.js
 * ================
 * Main JS application file for gvsigOL v2. This file
 * should be included in all pages. It controls some layout
 * options and implements exclusive gvsigOL plugins.
 *
 * @Author  Almsaeed Studio
 * @Support <http://www.almsaeedstudio.com>
 * @Email   <support@almsaeedstudio.com>
 * @version 2.3.0
 * @license MIT <http://opensource.org/licenses/MIT>
 */

//Make sure jQuery has been loaded before app.js
if (typeof jQuery === "undefined") {
	throw new Error("gvsigOL requires jQuery");
}

/* gvsigOL
 *
 * @type Object
 * @description $.gvsigOL is the main object for the template's app.
 *              It's used for implementing functions and options related
 *              to the template. Keeping everything wrapped in an object
 *              prevents conflict with other plugins and is a better
 *              way to organize our code.
 */
$.gvsigOL = {};

/* --------------------
 * - gvsigOL Options -
 * --------------------
 * Modify these options to suit your implementation
 */
$.gvsigOL.options = {
		//Add slimscroll to navbar menus
		//This requires you to load the slimscroll plugin
		//in every page before app.js
		navbarMenuSlimscroll: true,
		navbarMenuSlimscrollWidth: "3px", //The width of the scroll bar
		navbarMenuHeight: "200px", //The height of the inner menu
		//General animation speed for JS animated elements such as box collapse/expand and
		//sidebar treeview slide up/down. This options accepts an integer as milliseconds,
		//'fast', 'normal', or 'slow'
		animationSpeed: 500,
		//Sidebar push menu toggle button selector
		sidebarToggleSelector: "[data-toggle='offcanvas']",
		//Activate sidebar push menu
		sidebarPushMenu: true,
		//Activate sidebar slimscroll if the fixed layout is set (requires SlimScroll Plugin)
		sidebarSlimScroll: true,
		//Enable sidebar expand on hover effect for sidebar mini
		//This option is forced to true if both the fixed layout and sidebar mini
		//are used together
		sidebarExpandOnHover: false,
		//BoxRefresh Plugin
		enableBoxRefresh: true,
		//Bootstrap.js tooltip
		enableBSToppltip: true,
		BSTooltipSelector: "[data-toggle='tooltip']",
		//Enable Fast Click. Fastclick.js creates a more
		//native touch experience with touch devices. If you
		//choose to enable the plugin, make sure you load the script
		//before gvsigOL's app.js
		enableFastclick: true,
		//Box Widget Plugin. Enable this plugin
		//to allow boxes to be collapsed and/or removed
		enableBoxWidget: true,
		//Box Widget plugin options
		boxWidgetOptions: {
			boxWidgetIcons: {
				//Collapse icon
				collapse: 'fa-minus',
				//Open icon
				open: 'fa-plus',
				//Remove icon
				remove: 'fa-times'
			},
			boxWidgetSelectors: {
				//Remove button selector
				remove: '[data-widget="remove"]',
				//Collapse button selector
				collapse: '[data-widget="collapse"]'
			}
		},
		//Define the set of colors to use globally around the website
		colors: {
			lightBlue: "#3c8dbc",
			red: "#f56954",
			green: "#00a65a",
			aqua: "#00c0ef",
			yellow: "#f39c12",
			blue: "#0073b7",
			navy: "#001F3F",
			teal: "#39CCCC",
			olive: "#3D9970",
			lime: "#01FF70",
			orange: "#FF851B",
			fuchsia: "#F012BE",
			purple: "#8E24AA",
			maroon: "#D81B60",
			black: "#222222",
			gray: "#d2d6de"
		},
		//The standard screen sizes that bootstrap uses.
		//If you change these in the variables.less file, change
		//them here too.
		screenSizes: {
			xs: 480,
			sm: 768,
			md: 992,
			lg: 1200
		}
};

/* ------------------
 * - Implementation -
 * ------------------
 * The next block of code implements gvsigOL's
 * functions and plugins as specified by the
 * options above.
 */
$(function () {
	"use strict";

	//Fix for IE page transitions
	$("body").removeClass("hold-transition");

	//Extend options if external options exist
	if (typeof gvsigOLOptions !== "undefined") {
		$.extend(true,
				$.gvsigOL.options,
				gvsigOLOptions);
	}

	//Easy access to options
	var o = $.gvsigOL.options;

	//Set up the object
	_init();

	//Activate the layout maker
	$.gvsigOL.layout.activate();

	//Enable sidebar tree view controls
	$.gvsigOL.tree('.sidebar');

	//Add slimscroll to navbar dropdown
	if (o.navbarMenuSlimscroll && typeof $.fn.slimscroll != 'undefined') {
		$(".navbar .menu").slimscroll({
			height: o.navbarMenuHeight,
			alwaysVisible: false,
			size: o.navbarMenuSlimscrollWidth
		}).css("width", "100%");
	}

	//Activate sidebar push menu
	if (o.sidebarPushMenu) {
		$.gvsigOL.pushMenu.activate(o.sidebarToggleSelector);
	}

	//Activate Bootstrap tooltip
	if (o.enableBSToppltip) {
		$('body').tooltip({
			selector: o.BSTooltipSelector
		});
	}

	//Activate box widget
	if (o.enableBoxWidget) {
		$.gvsigOL.boxWidget.activate();
	}

	//Activate fast click
	if (o.enableFastclick && typeof FastClick != 'undefined') {
		FastClick.attach(document.body);
	}

	/*
	 * INITIALIZE BUTTON TOGGLE
	 * ------------------------
	 */
	$('.btn-group[data-toggle="btn-toggle"]').each(function () {
		var group = $(this);
		$(this).find(".btn").on('click', function (e) {
			group.find(".btn.active").removeClass("active");
			$(this).addClass("active");
			e.preventDefault();
		});

	});
});

/* ----------------------------------
 * - Initialize the gvsigOL Object -
 * ----------------------------------
 * All gvsigOL functions are implemented below.
 */
function _init() {
	'use strict';
	/* Layout
	 * ======
	 * Fixes the layout height in case min-height fails.
	 *
	 * @type Object
	 * @usage $.gvsigOL.layout.activate()
	 *        $.gvsigOL.layout.fix()
	 *        $.gvsigOL.layout.fixSidebar()
	 */
	$.gvsigOL.layout = {
			activate: function () {
				var _this = this;
				_this.fix();
				_this.fixSidebar();
				$(window, ".wrapper").resize(function () {
					_this.fix();
					_this.fixSidebar();
				});
			},
			fix: function () {
				//Get window height and the wrapper height
				var neg = $('.main-header').outerHeight() + $('.main-footer').outerHeight();
				var window_height = $(window).height();
				var sidebar_height = $(".sidebar").height();
				//Set the min-height of the content and sidebar based on the
				//the height of the document.
				if ($("body").hasClass("fixed")) {
					$(".content-wrapper, .right-side").css('min-height', window_height - $('.main-footer').outerHeight());
				} else {
					var postSetWidth;
					if (window_height >= sidebar_height) {
						$(".content-wrapper, .right-side").css('min-height', window_height - neg);
						postSetWidth = window_height - neg;
					} else {
						$(".content-wrapper, .right-side").css('min-height', sidebar_height);
						postSetWidth = sidebar_height;
					}

				}
			},
			fixSidebar: function () {
				//Make sure the body tag has the .fixed class
				if (!$("body").hasClass("fixed")) {
					if (typeof $.fn.slimScroll != 'undefined') {
						$(".sidebar").slimScroll({destroy: true}).height("auto");
					}
					return;
				} else if (typeof $.fn.slimScroll == 'undefined' && window.console) {
					window.console.error("Error: the fixed layout requires the slimscroll plugin!");
				}
				//Enable slimscroll for fixed layout
				if ($.gvsigOL.options.sidebarSlimScroll) {
					if (typeof $.fn.slimScroll != 'undefined') {
						//Destroy if it exists
						$(".sidebar").slimScroll({destroy: true}).height("auto");
						//Add slimscroll
						$(".sidebar").slimscroll({
							height: ($(window).height() - $(".main-header").height()) + "px",
							color: "rgba(0,0,0,0.2)",
							size: "3px"
						});
					}
				}
			}
	};

	/* PushMenu()
	 * ==========
	 * Adds the push menu functionality to the sidebar.
	 *
	 * @type Function
	 * @usage: $.gvsigOL.pushMenu("[data-toggle='offcanvas']")
	 */
	$.gvsigOL.pushMenu = {
			activate: function (toggleBtn) {
				//Get the screen sizes
				var screenSizes = $.gvsigOL.options.screenSizes;

				//Enable sidebar toggle
				$(toggleBtn).on('click', function (e) {
					e.preventDefault();

					//Enable sidebar push menu
					if ($(window).width() > (screenSizes.sm - 1)) {
						if ($("body").hasClass('sidebar-collapse')) {
							$("body").removeClass('sidebar-collapse').trigger('expanded.pushMenu');
						} else {
							$("body").addClass('sidebar-collapse').trigger('collapsed.pushMenu');
						}
					}
					//Handle sidebar push menu for small screens
					else {
						if ($("body").hasClass('sidebar-open')) {
							$("body").removeClass('sidebar-open').removeClass('sidebar-collapse').trigger('collapsed.pushMenu');
						} else {
							$("body").addClass('sidebar-open').trigger('expanded.pushMenu');
						}
					}
				});

				$(".content-wrapper").click(function () {
					//Enable hide menu when clicking on the content-wrapper on small screens
					if ($(window).width() <= (screenSizes.sm - 1) && $("body").hasClass("sidebar-open")) {
						$("body").removeClass('sidebar-open');
					}
				});

				//Enable expand on hover for sidebar mini
				if ($.gvsigOL.options.sidebarExpandOnHover
						|| ($('body').hasClass('fixed')
								&& $('body').hasClass('sidebar-mini'))) {
					this.expandOnHover();
				}
			},
			expandOnHover: function () {
				var _this = this;
				var screenWidth = $.gvsigOL.options.screenSizes.sm - 1;
				//Expand sidebar on hover
				$('.main-sidebar').hover(function () {
					if ($('body').hasClass('sidebar-mini')
							&& $("body").hasClass('sidebar-collapse')
							&& $(window).width() > screenWidth) {
						_this.expand();
					}
				}, function () {
					if ($('body').hasClass('sidebar-mini')
							&& $('body').hasClass('sidebar-expanded-on-hover')
							&& $(window).width() > screenWidth) {
						_this.collapse();
					}
				});
			},
			expand: function () {
				$("body").removeClass('sidebar-collapse').addClass('sidebar-expanded-on-hover');
			},
			collapse: function () {
				if ($('body').hasClass('sidebar-expanded-on-hover')) {
					$('body').removeClass('sidebar-expanded-on-hover').addClass('sidebar-collapse');
				}
			}
	};

	/* Tree()
	 * ======
	 * Converts the sidebar into a multilevel
	 * tree view menu.
	 *
	 * @type Function
	 * @Usage: $.gvsigOL.tree('.sidebar')
	 */
	$.gvsigOL.tree = function (menu) {
		var _this = this;
		var animationSpeed = $.gvsigOL.options.animationSpeed;
		$(document).on('click', menu + ' li a', function (e) {
			//Get the clicked link and the next element
			var $this = $(this);
			var checkElement = $this.next();

			//Check if the next element is a menu and is visible
			if ((checkElement.is('.treeview-menu')) && (checkElement.is(':visible'))) {
				//Close the menu
				checkElement.slideUp(animationSpeed, function () {
					checkElement.removeClass('menu-open');
					//Fix the layout in case the sidebar stretches over the height of the window
					//_this.layout.fix();
				});
				checkElement.parent("li").removeClass("active");
			}
			//If the menu is not visible
			else if ((checkElement.is('.treeview-menu')) && (!checkElement.is(':visible'))) {
				//Get the parent menu
				var parent = $this.parents('ul').first();
				//Close all open menus within the parent
				var ul = parent.find('ul:visible').slideUp(animationSpeed);
				//Remove the menu-open class from the parent
				ul.removeClass('menu-open');
				//Get the parent li
				var parent_li = $this.parent("li");

				//Open the target menu and add the menu-open class
				checkElement.slideDown(animationSpeed, function () {
					//Add the class active to the parent li
					checkElement.addClass('menu-open');
					parent.find('li.active').removeClass('active');
					parent_li.addClass('active');
					//Fix the layout in case the sidebar stretches over the height of the window
					_this.layout.fix();
				});
			}
			//if this isn't a link, prevent the page from being redirected
			if (checkElement.is('.treeview-menu')) {
				e.preventDefault();
			}
		});
	};

	/* BoxWidget
	 * =========
	 * BoxWidget is a plugin to handle collapsing and
	 * removing boxes from the screen.
	 *
	 * @type Object
	 * @usage $.gvsigOL.boxWidget.activate()
	 *        Set all your options in the main $.gvsigOL.options object
	 */
	$.gvsigOL.boxWidget = {
			selectors: $.gvsigOL.options.boxWidgetOptions.boxWidgetSelectors,
			icons: $.gvsigOL.options.boxWidgetOptions.boxWidgetIcons,
			animationSpeed: $.gvsigOL.options.animationSpeed,
			activate: function (_box) {
				var _this = this;
				if (!_box) {
					_box = document; // activate all boxes per default
				}
				//Listen for collapse event triggers
				$(_box).on('click', _this.selectors.collapse, function (e) {
					e.preventDefault();
					_this.collapse($(this));
				});

				//Listen for remove event triggers
				$(_box).on('click', _this.selectors.remove, function (e) {
					e.preventDefault();
					_this.remove($(this));
				});
			},
			collapse: function (element) {
				var _this = this;
				//Find the box parent
				var box = element.parents(".box").first();
				//Find the body and the footer
				var box_content = box.find("> .box-body, > .box-footer, > form  >.box-body, > form > .box-footer");
				if (!box.hasClass("collapsed-box")) {
					//Convert minus into plus
					element.children(":first")
					.removeClass(_this.icons.collapse)
					.addClass(_this.icons.open);
					//Hide the content
					box_content.slideUp(_this.animationSpeed, function () {
						box.addClass("collapsed-box");
					});
				} else {
					//Convert plus into minus
					element.children(":first")
					.removeClass(_this.icons.open)
					.addClass(_this.icons.collapse);
					//Show the content
					box_content.slideDown(_this.animationSpeed, function () {
						box.removeClass("collapsed-box");
					});
				}
			},
			remove: function (element) {
				//Find the box parent
				var box = element.parents(".box").first();
				box.slideUp(this.animationSpeed);
			}
	};
}

/* ------------------
 * - Custom Plugins -
 * ------------------
 * All custom plugins are defined below.
 */

/*
 * BOX REFRESH BUTTON
 * ------------------
 * This is a custom plugin to use with the component BOX. It allows you to add
 * a refresh button to the box. It converts the box's state to a loading state.
 *
 * @type plugin
 * @usage $("#box-widget").boxRefresh( options );
 */
(function ($) {

	"use strict";

	$.fn.boxRefresh = function (options) {

		// Render options
		var settings = $.extend({
			//Refresh button selector
			trigger: ".refresh-btn",
			//File source to be loaded (e.g: ajax/src.php)
			source: "",
			//Callbacks
			onLoadStart: function (box) {
				return box;
			}, //Right after the button has been clicked
			onLoadDone: function (box) {
				return box;
			} //When the source has been loaded

		}, options);

		//The overlay
		var overlay = $('<div class="overlay"><div class="fa fa-refresh fa-spin"></div></div>');

		return this.each(function () {
			//if a source is specified
			if (settings.source === "") {
				if (window.console) {
					window.console.log("Please specify a source first - boxRefresh()");
				}
				return;
			}
			//the box
			var box = $(this);
			//the button
			var rBtn = box.find(settings.trigger).first();

			//On trigger click
			rBtn.on('click', function (e) {
				e.preventDefault();
				//Add loading overlay
				start(box);

				//Perform ajax call
				box.find(".box-body").load(settings.source, function () {
					done(box);
				});
			});
		});

		function start(box) {
			//Add overlay and loading img
			box.append(overlay);

			settings.onLoadStart.call(box);
		}

		function done(box) {
			//Remove overlay and loading img
			box.find(overlay).remove();

			settings.onLoadDone.call(box);
		}

	};

})(jQuery);

/*
 * EXPLICIT BOX ACTIVATION
 * -----------------------
 * This is a custom plugin to use with the component BOX. It allows you to activate
 * a box inserted in the DOM after the app.js was loaded.
 *
 * @type plugin
 * @usage $("#box-widget").activateBox();
 */
(function ($) {

	'use strict';

	$.fn.activateBox = function () {
		$.gvsigOL.boxWidget.activate(this);
	};

})(jQuery);

/*
 * TODO LIST CUSTOM PLUGIN
 * -----------------------
 * This plugin depends on iCheck plugin for checkbox and radio inputs
 *
 * @type plugin
 * @usage $("#todo-widget").todolist( options );
 */
(function ($) {

	'use strict';

	$.fn.todolist = function (options) {
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

			if (typeof $.fn.iCheck != 'undefined') {
				$('input', this).on('ifChecked', function () {
					var ele = $(this).parents("li").first();
					ele.toggleClass("done");
					settings.onCheck.call(ele);
				});

				$('input', this).on('ifUnchecked', function () {
					var ele = $(this).parents("li").first();
					ele.toggleClass("done");
					settings.onUncheck.call(ele);
				});
			} else {
				$('input', this).on('change', function () {
					var ele = $(this).parents("li").first();
					ele.toggleClass("done");
					if ($('input', ele).is(":checked")) {
						settings.onCheck.call(ele);
					} else {
						settings.onUncheck.call(ele);
					}
				});
			}
		});
	};
}(jQuery));