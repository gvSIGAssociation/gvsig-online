(function(factory) {

    if (typeof define === 'function' && define.amd) {
        define(['jquery'], factory);
    } else if (typeof module === 'object' && module.exports) {
        module.exports = factory(require('jquery'));
    } else {
        factory(jQuery);
    }

}(function($) {

    var $document = $(window.document),
        instanceNum = 0,
        eventStringRE = /\w\b/g,
        keyMap = {
            13: 'enter',
            27: 'escape',
            40: 'downArrow',
            38: 'upArrow'
        };

    function Fastsearch(inputElement, options) {

        this.init.apply(this, arguments);

    }

    $.extend(Fastsearch.prototype, {

        init: function(inputElement, options) {

            options = this.options = $.extend(true, {}, Fastsearch.defaults, options);

            this.$input = $(inputElement);
            this.$el = options.wrapSelector instanceof $ ? options.wrapSelector : this.$input.closest(options.wrapSelector);

            Fastsearch.pickTo(options, this.$el.data(), [
                'url', 'onItemSelect', 'noResultsText', 'inputIdName', 'apiInputName'
            ]);

            options.url = options.url || this.$el.attr('action');

            this.ens = '.fastsearch' + (++instanceNum);
            this.itemSelector = Fastsearch.selectorFromClass(options.itemClass);
            this.focusedItemSelector = Fastsearch.selectorFromClass(options.focusedItemClass);

            this.events();

        },

        namespaceEvents: function(events) {

            var eventNamespace = this.ens;

            return events.replace(eventStringRE, function(match) {
                return match + eventNamespace;
            });

        },

        events: function() {

            var self = this,
                options = this.options;

            this.$input.on(this.namespaceEvents('keyup focus click'), function(e) {

                keyMap[e.keyCode] !== 'enter' && self.handleTyping();

            }).on(this.namespaceEvents('keydown'), function(e) {

                keyMap[e.keyCode] === 'enter' && options.preventSubmit && e.preventDefault();

                if (self.hasResults && self.resultsOpened) {

                    switch (keyMap[e.keyCode]) {
                        case 'downArrow': e.preventDefault(); self.navigateItem('down'); break;
                        case 'upArrow': e.preventDefault(); self.navigateItem('up'); break;
                        case 'enter': self.onEnter(e); break;
                    }

                }

            });

            this.$el.on(this.namespaceEvents('click'), this.itemSelector, function(e) {

                e.preventDefault();
                self.handleItemSelect($(this));

            });

            options.mouseEvents && this.$el.on(this.namespaceEvents('mouseleave'), this.itemSelector, function(e) {

                $(this).removeClass(options.focusedItemClass);

            }).on(this.namespaceEvents('mouseenter'), this.itemSelector, function(e) {

                self.$resultItems.removeClass(options.focusedItemClass);
                $(this).addClass(options.focusedItemClass);

            });

        },

        handleTyping: function() {

            var inputValue = $.trim(this.$input.val()),
                self = this;

            if (inputValue.length < this.options.minQueryLength) {

                this.hideResults();

            } else if (inputValue === this.query) {

                this.showResults();

            } else {

                clearTimeout(this.keyupTimeout);

                this.keyupTimeout = setTimeout(function() {

                    self.$el.addClass(self.options.loadingClass);

                    self.query = inputValue;

                    self.getResults(function(data) {

                        self.showResults(self.storeResponse(data).generateResults(data));

                    });

                }, this.options.typeTimeout);

            }

        },

        getResults: function(callback) {

            var self = this,
                options = this.options,
                formValues = this.$el.find('input, textarea, select').serializeArray();

            if (options.apiInputName) {
                formValues.push({'name': options.apiInputName, 'value': this.$input.val()});
            }

            $.get(options.url, formValues, function(data) {

                callback(options.parseResponse ? options.parseResponse.call(self, data, self) : data);

            });

        },

        storeResponse: function(data) {

            this.responseData = data;
            this.hasResults = data.length !== 0;

            return this;

        },

        generateResults: function(data) {

            var $allResults = $('<div>'),
                options = this.options;

            if (options.template) {
                return $(options.template(data, this));
            }

            if (data.length === 0) {

                $allResults.html(
                    '<p class="' + options.noResultsClass + '">' +
                        (typeof options.noResultsText === 'function' ? options.noResultsText.call(this) : options.noResultsText) +
                    '</p>'
                );

            } else {

                if (this.options.responseType === 'html') {

                    $allResults.html(data);

                } else {

                    this['generate' + (data[0][options.responseFormat.groupItems] ? 'GroupedResults' : 'SimpleResults')](data, $allResults);

                }

            }

            return $allResults.children();

        },

        generateSimpleResults: function(data, $cont) {

            var self = this;

            this.itemModels = data;

            $.each(data, function(i, item) {
                $cont.append(self.generateItem(item));
            });

        },

        generateGroupedResults: function(data, $cont) {

            var self = this,
                options = this.options,
                format = options.responseFormat;

            this.itemModels = [];

            $.each(data, function(i, groupData) {

                var $group = $('<div class="' + options.groupClass + '">').appendTo($cont);

                groupData[format.groupCaption] && $group.append(
                    '<h3 class="' + options.groupTitleClass + '">' + groupData[format.groupCaption] + '</h3>'
                );

                $.each(groupData.items, function(i, item) {

                    self.itemModels.push(item);
                    $group.append(self.generateItem(item));

                });

                options.onGroupCreate && options.onGroupCreate.call(self, $group, groupData, self);

            });

        },

        generateItem: function(item) {

            var options = this.options,
                format = options.responseFormat,
                url = item[format.url],
                html = item[format.html] || item[format.label],
                $tag = $('<' + (url ? 'a' : 'span') + '>').html(html).addClass(options.itemClass);

            url && $tag.attr('href', url);

            options.onItemCreate && options.onItemCreate.call(this, $tag, item, this);

            return $tag;

        },

        showResults: function($content) {

            if (!$content && this.resultsOpened) {
                return;
            }

            this.$el.removeClass(this.options.loadingClass).addClass(this.options.resultsOpenedClass);

            if (this.options.flipOnBottom) {
                this.checkDropdownPosition();
            }

            this.$resultsCont = this.$resultsCont || $('<div>').addClass(this.options.resultsContClass).appendTo(this.$el);

            if ($content) {

                this.$resultsCont.html($content);
                this.$resultItems = this.$resultsCont.find(this.itemSelector);
                this.options.onResultsCreate && this.options.onResultsCreate.call(this, this.$resultsCont, this.responseData, this);

            }

            if (!this.resultsOpened) {

                this.documentCancelEvents('on');
                this.$input.trigger('openingResults');

            }

            if (this.options.focusFirstItem && this.$resultItems && this.$resultItems.length) {
                this.navigateItem('down');
            }

            this.resultsOpened = true;

        },

        checkDropdownPosition: function() {

            var flipOnBottom = this.options.flipOnBottom;
            var offset = typeof flipOnBottom === 'boolean' && flipOnBottom ? 400 : flipOnBottom;
            var isFlipped = this.$input.offset().top + offset > $document.height();

            this.$el.toggleClass(this.options.resultsFlippedClass, isFlipped);

        },

        documentCancelEvents: function(setup, onCancel) {

            var self = this;

            if (setup === 'off' && this.closeEventsSetuped) {

                $document.off(this.ens);
                this.closeEventsSetuped = false;
                return;

            } else if (setup === 'on' && !this.closeEventsSetuped) {

                $document.on(this.namespaceEvents('click keyup'), function(e) {

                    if (keyMap[e.keyCode] === 'escape' || (!$(e.target).is(self.$el) && !$.contains(self.$el.get(0), e.target) && $.contains(document.documentElement, e.target))) {

                        onCancel ? onCancel.call(self) : self.hideResults();

                    }

                });

                this.closeEventsSetuped = true;

            }

        },

        navigateItem: function(direction) {

            var $currentItem = this.$resultItems.filter(this.focusedItemSelector),
                maxPosition = this.$resultItems.length - 1;

            if ($currentItem.length === 0) {

                this.$resultItems.eq(direction === 'up' ? maxPosition : 0).addClass(this.options.focusedItemClass);
                return;

            }

            var currentPosition = this.$resultItems.index($currentItem),
                nextPosition = direction === 'up' ? currentPosition - 1 : currentPosition + 1;

            nextPosition > maxPosition && (nextPosition = 0);
            nextPosition < 0 && (nextPosition = maxPosition);

            $currentItem.removeClass(this.options.focusedItemClass);

            this.$resultItems.eq(nextPosition).addClass(this.options.focusedItemClass);

        },

        navigateDown: function() {

            this.navigateItem('down');

        },

        navigateUp: function() {

            this.navigateItem('up');

        },

        onEnter: function(e) {

            var $currentItem = this.$resultItems.filter(this.focusedItemSelector);

            if ($currentItem.length) {
                e.preventDefault();
                this.handleItemSelect($currentItem);
            }

        },

        handleItemSelect: function($item) {

            var selectOption = this.options.onItemSelect,
                model = this.itemModels.length ? this.itemModels[this.$resultItems.index($item)] : {};

            this.$input.trigger('itemSelected');

            if (selectOption === 'fillInput') {

                this.fillInput(model);

            } else if (selectOption === 'follow') {

                window.location.href = $item.attr('href');

            } else if (typeof selectOption === 'function') {

                selectOption.call(this, $item, model, this);

            }

        },

        fillInput: function(model) {

            var options = this.options,
                format = options.responseFormat;

            this.query = model[format.label];
            this.$input.val(model[format.label]).trigger('change');

            if (options.fillInputId && model.id) {

                if (!this.$inputId) {

                    var inputIdName = options.inputIdName || this.$input.attr('name') + '_id';

                    this.$inputId = this.$el.find('input[name="' + inputIdName + '"]');

                    if (!this.$inputId.length) {
                        this.$inputId = $('<input type="hidden" name="' + inputIdName + '" />').appendTo(this.$el);
                    }

                }

                this.$inputId.val(model.id).trigger('change');

            }

            this.hideResults();

        },

        hideResults: function() {

            if (this.resultsOpened) {

                this.resultsOpened = false;
                this.$el.removeClass(this.options.resultsOpenedClass);
                this.$input.trigger('closingResults');
                this.documentCancelEvents('off');

            }

            return this;

        },

        clear: function() {

            this.hideResults();
            this.$input.val('').trigger('change');

            return this;

        },

        destroy: function() {

            $document.off(this.ens);

            this.$input.off(this.ens);

            this.$el.off(this.ens)
                .removeClass(this.options.resultsOpenedClass)
                .removeClass(this.options.loadingClass);

            if (this.$resultsCont) {

                this.$resultsCont.remove();
                delete this.$resultsCont;

            }

            delete this.$el.data().fastsearch;

        }

    });

    $.extend(Fastsearch, {

        pickTo: function(dest, src, keys) {

            $.each(keys, function(i, key) {
                dest[key] = (src && src[key]) || dest[key];
            });

            return dest;

        },

        selectorFromClass: function(classes) {

            return '.' + classes.replace(/\s/g, '.');

        }

    });

    Fastsearch.defaults = {
        wrapSelector: 'form', // fastsearch container defaults to closest form. Provide selector for something other
        url: null, // plugin will get data from data-url propery, url option or container action attribute
        responseType: 'JSON', // default expected server response type - can be set to html if that is what server returns
        preventSubmit: false, // prevent submit of form with enter keypress

        resultsContClass: 'fs_results', // html classes
        resultsOpenedClass: 'fsr_opened',
        resultsFlippedClass: 'fsr_flipped',
        groupClass: 'fs_group',
        itemClass: 'fs_result_item',
        groupTitleClass: 'fs_group_title',
        loadingClass: 'loading',
        noResultsClass: 'fs_no_results',
        focusedItemClass: 'focused',

        typeTimeout: 140, // try not to hammer server with request for each keystroke if possible
        minQueryLength: 2, // minimal number of characters needed for plugin to send request to server

        template: null, // provide your template function if you need one - function(data, fastsearchApi)
        mouseEvents: !('ontouchstart' in window || navigator.maxTouchPoints > 0 || navigator.msMaxTouchPoints > 0), // detect if client is touch enabled so plugin can decide if mouse specific events should be set.
        focusFirstItem: false,
        flipOnBottom: false,

        responseFormat: { // Adjust where plugin looks for data in your JSON server response
            url: 'url',
            html: 'html',
            label: 'label',
            groupCaption: 'caption',
            groupItems: 'items'
        },

        fillInputId: true, // on item select plugin will try to write selected id from item data model to input
        inputIdName: null, // on item select plugin will try to write selected id from item data model to input with this name

        apiInputName: null, // by default plugin will post input name as query parameter - you can provide custom one here

        noResultsText: 'No results found',
        onItemSelect: 'follow', // by default plugin follows selected link - other options available are "fillInput" and custom callback - function($item, model, fastsearchApi)

        parseResponse: null, // parse server response with your handler and return processed data - function(response, fastsearchApi)
        onResultsCreate: null, // adjust results element - function($allResults, data, fastsearchApi)
        onGroupCreate: null, // adjust group element when created - function($group, groupModel, fastsearchApi)
        onItemCreate: null // adjust item element when created - function($item, model, fastsearchApi)
    };

    $.fastsearch = Fastsearch;

    $.fn.fastsearch = function(options) {
        return this.each(function() {
            if (!$.data(this, 'fastsearch')) {
                $.data(this, 'fastsearch', new Fastsearch(this, options));
            }
        });
    };

    return $;

}));
