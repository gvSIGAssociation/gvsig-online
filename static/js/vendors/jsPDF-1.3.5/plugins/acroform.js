/**
 * jsPDF AcroForm Plugin
 * Copyright (c) 2016 Alexander Weidt, https://github.com/BiggA94
 *
 * Licensed under the MIT License.
 * http://opensource.org/licenses/mit-license
 */

(function (jsPDFAPI, globalObj) {
    'use strict';

    var scope;
    var pageHeight;
    var scaleFactor = 1;
    var inherit = function (child, parent) {
            var ObjectCreate = Object.create || function (o) {
                    var F = function () {
                    };
                    F.prototype = o;
                    return new F();
                };
            child.prototype = Object.create(parent.prototype);
            child.prototype.constructor = child;
    };
    var scale = function (x) {
        return (x * (scaleFactor / 1));// 1 = (96 / 72)
    };
    var antiScale = function (x) {
        return ((1 / scaleFactor ) * x);
    };
    
    /**
    Returns a widths of string in a given font, if the font size is set as 1 point.

    In other words, this is "proportional" value. For 1 unit of font size, the length
    of the string will be that much.

    Multiply by font size to get actual width in *points*
    Then divide by 72 to get inches or divide by (72/25.6) to get 'mm' etc.

    @public
    @function
    @param
    @returns {Type}
    */
    var getStringUnitWidth = function(text, options) {
        var result = 0;
        if (typeof TTFFont === "function" && options.font.metadata instanceof TTFFont === true) {
            result = options.font.metadata.widthOfString(text, options.fontSize, options.charSpace);
        } else {
            result = getArraySum(getCharWidthsArray(text, options)) * options.fontSize;
        }
        return result;
    };

    /**
    Returns an array of length matching length of the 'word' string, with each
    cell ocupied by the width of the char in that position.

    @function
    @param word {String}
    @param widths {Object}
    @param kerning {Object}
    @returns {Array}
    */
    function getCharWidthsArray(text, options) {
        options = options || {};

        var widths = options.widths ? options.widths : options.font.metadata.Unicode.widths;
        var widthsFractionOf = widths.fof ? widths.fof : 1;
        var kerning = options.kerning ? options.kerning : options.font.metadata.Unicode.kerning;
        var kerningFractionOf = kerning.fof ? kerning.fof : 1;

        var i;
        var l;
        var char_code;
        var prior_char_code = 0; //for kerning
        var default_char_width = widths[0] || widthsFractionOf;
        var output = [];

        for (i = 0, l = text.length; i < l; i++) {
            char_code = text.charCodeAt(i)
            output.push(
                ( widths[char_code] || default_char_width ) / widthsFractionOf +
                ( kerning[char_code] && kerning[char_code][prior_char_code] || 0 ) / kerningFractionOf
            );
            prior_char_code = char_code;
        }

        return output
    }
    

    var getArraySum = function(array) {
        var i = array.length;
        var output = 0;
        
        while(i) {
            ;i--;
            output += array[i];
        }
        
        return output;
    }
    
    var createFormXObject = function (formObject) {
        var xobj = new AcroFormXObject;
        var height = AcroFormAppearance.internal.getHeight(formObject) || 0;
        var width = AcroFormAppearance.internal.getWidth(formObject) || 0;
        xobj.BBox = [0, 0, width.toFixed(2), height.toFixed(2)];
        return xobj;
    };
    
    var setBitPosition = function (variable, position, value) {
        variable = variable || 0;
        value = value || 1;

        var bitMask = 1;
        bitMask = bitMask << (position - 1);

        if (value == 1) {
            // Set the Bit to 1
            var variable = variable | bitMask;
        } else {
            // Set the Bit to 0
            var variable = variable & (~bitMask);
        }

        return variable;
    };
    
    var getBitPosition = function (variable, position) {
        variable = variable || 0;
        var bitMask = 1;
        bitMask = bitMask << (position - 1);
        return variable | bitMask;
    };
    

    
    /**
     * Calculating the Ff entry:
     *
     * The Ff entry contains flags, that have to be set bitwise
     * In the Following the number in the Comment is the BitPosition
     */
    var calculateFlagsOnOptions = function (flags, opts, PDFVersion) {
        var PDFVersion = PDFVersion || 1.3;
        var flags = flags || 0;
        
        // 1, readOnly
        if (opts.readOnly == true) {
            flags = setBitPosition(flags, 1);
        }

        // 2, required
        if (opts.required == true) {
            flags = setBitPosition(flags, 2);
        }

        // 4, noExport
        if (opts.noExport == true) {
            flags = setBitPosition(flags, 3);
        }

        // 13, multiline
        if (opts.multiline == true) {
            flags = setBitPosition(flags, 13);
        }

        // 14, Password
        if (opts.password) {
            flags = setBitPosition(flags, 14);
        }

        // 15, NoToggleToOff (Radio buttons only
        if (opts.noToggleToOff) {
            flags = setBitPosition(flags, 15);
        }

        //16, Radio
        if (opts.radio) {
            flags = setBitPosition(flags, 16);
        }
        
        // 17, Pushbutton
        if (opts.pushbutton) {
            flags = setBitPosition(flags, 17);
        }
        
        // 18, Combo (If not set, the choiceField is a listBox!!)
        if (opts.combo) {
            flags = setBitPosition(flags, 18);
        }

        // 19, Edit
        if (opts.edit) {
            flags = setBitPosition(flags, 19);
        }

        // 20, Sort
        if (opts.sort) {
            flags = setBitPosition(flags, 20);
        }
        
        // 21, FileSelect, PDF 1.4...
        if (opts.fileSelect && PDFVersion >= 1.4) {
            flags = setBitPosition(flags, 21);
        }

        // 22, MultiSelect (PDF 1.4)
        if (opts.multiSelect && PDFVersion >= 1.4) {
            flags = setBitPosition(flags, 22);
        }

        // 23, DoNotSpellCheck (PDF 1.4)
        if (opts.doNotSpellCheck && PDFVersion >= 1.4) {
            flags = setBitPosition(flags, 23);
        }

        // 24, DoNotScroll (PDF 1.4)
        if (opts.doNotScroll == true && PDFVersion >= 1.4) {
            flags = setBitPosition(flags, 24);
        }
        
        // 25, RichText (PDF 1.4)
        if (opts.richText && PDFVersion >= 1.4) {
            flags = setBitPosition(flags, 25);
        }
        
        return flags;
    }
    
    var calculateColor = function (r, g, b) {
        var color = new Array(3);
        color.r = r | 0;
        color.g = g | 0;
        color.b = b | 0;
        return color;
    };

    var calculateCoordinates = function (args) {
        var x = args[0];
        var y = args[1];
        var w = args[2];
        var h = args[3];

        var coordinates = {};

        if (Array.isArray(x)) {
            x[0] = scale(x[0]);
            x[1] = scale(x[1]);
            x[2] = scale(x[2]);
            x[3] = scale(x[3]);
        } else {
            x = scale(x);
            y = scale(y);
            w = scale(w);
            h = scale(h);
        }
            coordinates.lowerLeft_X = x || 0;
            coordinates.lowerLeft_Y = scale(pageHeight) - y - h || 0;
            coordinates.upperRight_X = x + w || 0;
            coordinates.upperRight_Y = scale(pageHeight) - y || 0;
    
            return [coordinates.lowerLeft_X.toFixed(2), coordinates.lowerLeft_Y.toFixed(2), coordinates.upperRight_X.toFixed(2), coordinates.upperRight_Y.toFixed(2)];
        };
        
        var calculateAppearanceStream = function (formObject) {
            if (formObject.appearanceStreamContent) {
                // If appearanceStream is already set, use it
                return formObject.appearanceStreamContent;
            }

            if (!formObject.V && !formObject.DV) {
                return;
            }

            // else calculate it

            var stream = '';
            var text = formObject.V || formObject.DV;
            var calcRes = calculateX(formObject, text);

            stream += '/Tx BMC\n' +
                'q\n' +
                    //color + '\n' +
                '/F1 ' + calcRes.fontSize.toFixed(2) + ' Tf\n' +
                    // Text Matrix
                '1 0 0 1 0 0 Tm\n';
            // Begin Text
            stream += 'BT\n';
            stream += calcRes.text;
            // End Text
            stream += 'ET\n';
            stream += 'Q\n' +
                'EMC\n';

            var appearanceStreamContent = new createFormXObject(formObject);
            appearanceStreamContent.stream = stream;

            var appearance = {
                N: {
                    'Normal': appearanceStreamContent
                }
            };

            return appearanceStreamContent;
        };
        
        var calculateX = function (formObject, text, font, maxFontSize) {
            var maxFontSize = maxFontSize || 12;
            var font = font || "helvetica";
            var returnValue = {
                text: "",
                fontSize: ""
            };
            // Remove Brackets
            text = (text.substr(0, 1) == '(') ? text.substr(1) : text;
            text = (text.substr(text.length - 1) == ')') ? text.substr(0, text.length - 1) : text;
            // split into array of words
            var textSplit = text.split(' ');

            /**
             * the color could be ((alpha)||(r,g,b)||(c,m,y,k))
             * @type {string}
             */
            var color = "0 g\n";
            var fontSize = maxFontSize; // The Starting fontSize (The Maximum)
            var lineSpacing = 2;
            var borderPadding = 2;


            var height = AcroFormAppearance.internal.getHeight(formObject) || 0;
            height = (height < 0) ? -height : height;
            var width = AcroFormAppearance.internal.getWidth(formObject) || 0;
            width = (width < 0) ? -width : width;

            var isSmallerThanWidth = function (i, lastLine, fontSize) {
                if (i + 1 < textSplit.length) {
                    var tmp = lastLine + " " + textSplit[i + 1];
                    var TextWidth = ((calculateFontSpace(tmp, fontSize + "px", font).width));
                    var FieldWidth = (width - 2 * borderPadding);
                    return (TextWidth <= FieldWidth);
                } else {
                    return false;
                }
            };


            fontSize++;
            FontSize: while (true) {
                var text = "";
                fontSize--;
                var textHeight = calculateFontSpace("3", fontSize + "px", font).height;
                var startY = (formObject.multiline) ? height - fontSize : (height - textHeight) / 2;
                startY += lineSpacing;
                var startX = -borderPadding;

                var lastX = startX, lastY = startY;
                var firstWordInLine = 0, lastWordInLine = 0;
                var lastLength = 0;

                var y = 0;
                if (fontSize == 0) {
                    // In case, the Text doesn't fit at all
                    fontSize = 12;
                    text = "(...) Tj\n";
                    text += "% Width of Text: " + calculateFontSpace(text, "1px").width + ", FieldWidth:" + width + "\n";
                    break;
                }

                lastLength = calculateFontSpace(textSplit[0] + " ", fontSize + "px", font).width;

                var lastLine = "";
                var lineCount = 0;
                Line:
                    for (var i in textSplit) {
                        lastLine += textSplit[i] + " ";
                        // Remove last blank
                        lastLine = (lastLine.substr(lastLine.length - 1) == " ") ? lastLine.substr(0, lastLine.length - 1) : lastLine;
                        var key = parseInt(i);
                        lastLength = calculateFontSpace(lastLine + " ", fontSize + "px", font).width;
                        var nextLineIsSmaller = isSmallerThanWidth(key, lastLine, fontSize);
                        var isLastWord = i >= textSplit.length - 1;
                        if (nextLineIsSmaller && !isLastWord) {
                            lastLine += " ";
                            continue; // Line
                        } else if (!nextLineIsSmaller && !isLastWord) {
                            if (!formObject.multiline) {
                                continue FontSize;
                            } else {
                                if (((textHeight + lineSpacing) * (lineCount + 2) + lineSpacing) > height) {
                                    // If the Text is higher than the FieldObject
                                    continue FontSize;
                                }
                                lastWordInLine = key;
                                // go on
                            }
                        } else if (isLastWord) {
                            lastWordInLine = key;
                        } else {
                            if (formObject.multiline && ((textHeight + lineSpacing) * (lineCount + 2) + lineSpacing) > height) {
                                // If the Text is higher than the FieldObject
                                continue FontSize;
                            }
                        }

                        var line = '';

                        for (var x = firstWordInLine; x <= lastWordInLine; x++) {
                            line += textSplit[x] + ' ';
                        }

                        // Remove last blank
                        line = (line.substr(line.length - 1) == " ") ? line.substr(0, line.length - 1) : line;
                        //lastLength -= blankSpace.width;
                        lastLength = calculateFontSpace(line, fontSize + "px", font).width;

                        // Calculate startX
                        switch (formObject.Q) {
                            case 2: // Right justified
                                startX = (width - lastLength - borderPadding);
                                break;
                            case 1:// Q = 1 := Text-Alignment: Center
                                startX = (width - lastLength) / 2;
                                break;
                            case 0:
                            default:
                                startX = borderPadding;
                                break;
                        }
                        text += (startX.toFixed(2)) + ' ' + (lastY.toFixed(2)) + ' Td\n';
                        text += '(' + line + ') Tj\n';
                        // reset X in PDF
                        text += (-startX.toFixed(2)) + ' 0 Td\n';

                        // After a Line, adjust y position
                        lastY = -(fontSize + lineSpacing);
                        lastX = startX;

                        // Reset for next iteration step
                        lastLength = 0;
                        firstWordInLine = lastWordInLine + 1;
                        lineCount++;

                        lastLine = "";
                        continue Line;
                    }
                break;
            }

            returnValue.text = text;
            returnValue.fontSize = fontSize;

            return returnValue;
        };
        /*
         * small workaround for calculating the TextMetric approximately
         * @param text
         * @param fontsize
         * @returns {TextMetrics} (Has Height and Width)
         */
        var calculateFontSpace = function (text, fontsize, fonttype) {
            var fonttype = fonttype || "helvetica";
            var font = scope.internal.getFont(fonttype);
            var width = getStringUnitWidth(text, {font : font, fontSize: parseFloat(fontsize), charSpace: 0});
            var height = getStringUnitWidth("3", {font : font, fontSize: parseFloat(fontsize), charSpace: 0}) * 1.5;
            var result = {height: height, width: width};
            return result;
        };

    
    var acroformPluginTemplate = {
            fields: [],
            xForms: [],
            /**
             * acroFormDictionaryRoot contains information about the AcroForm Dictionary
             * 0: The Event-Token, the AcroFormDictionaryCallback has
             * 1: The Object ID of the Root
             */
            acroFormDictionaryRoot: null,
            /**
             * After the PDF gets evaluated, the reference to the root has to be reset,
             * this indicates, whether the root has already been printed out
             */
            printedOut: false,
            internal: null,
            isInitialized: false
    };
    
    var annotReferenceCallback = function () {
        for (var i in scope.internal.acroformPlugin.acroFormDictionaryRoot.Fields) {
            var formObject = scope.internal.acroformPlugin.acroFormDictionaryRoot.Fields[i];
            // add Annot Reference!
            if (formObject.hasAnnotation) {
                // If theres an Annotation Widget in the Form Object, put the Reference in the /Annot array
                createAnnotationReference.call(scope, formObject);
            }
        }
    };
    
    var putForm = function (formObject) {
        if (scope.internal.acroformPlugin.printedOut) {
            scope.internal.acroformPlugin.printedOut = false;
            scope.internal.acroformPlugin.acroFormDictionaryRoot = null;
        }
        if (!scope.internal.acroformPlugin.acroFormDictionaryRoot) {
            initializeAcroForm.call(scope);
        }
        scope.internal.acroformPlugin.acroFormDictionaryRoot.Fields.push(formObject);
    };
    /**
     * Create the Reference to the widgetAnnotation, so that it gets referenced in the Annot[] int the+
     * (Requires the Annotation Plugin)
     */
    var createAnnotationReference = function (object) {
        var options = {
            type: 'reference',
            object: object
        };
        scope.annotationPlugin.annotations[scope.internal.getPageInfo(object.page).pageNumber].push(options);
    };

    // Callbacks

    var putCatalogCallback = function () {
        //Put reference to AcroForm to DocumentCatalog
        if (typeof scope.internal.acroformPlugin.acroFormDictionaryRoot != 'undefined') { // for safety, shouldn't normally be the case
            scope.internal.write('/AcroForm ' + scope.internal.acroformPlugin.acroFormDictionaryRoot.objId + ' '
                + 0 + ' R');
        } else {
            console.log('Root missing...');
        }
    };


    /**
     * Adds /Acroform X 0 R to Document Catalog,
     * and creates the AcroForm Dictionary
     */
    var AcroFormDictionaryCallback = function () {
        // Remove event
        scope.internal.events.unsubscribe(scope.internal.acroformPlugin.acroFormDictionaryRoot._eventID);

        delete scope.internal.acroformPlugin.acroFormDictionaryRoot._eventID;

        scope.internal.acroformPlugin.printedOut = true;
    };

    /**
     * Creates the single Fields and writes them into the Document
     *
     * If fieldArray is set, use the fields that are inside it instead of the fields from the AcroRoot
     * (for the FormXObjects...)
     */
    var createFieldCallback = function (fieldArray) {
        var standardFields = (!fieldArray);

        if (!fieldArray) {
            // in case there is no fieldArray specified, we want to print out the Fields of the AcroForm
            // Print out Root
            scope.internal.newObjectDeferredBegin(scope.internal.acroformPlugin.acroFormDictionaryRoot.objId);
            scope.internal.out(scope.internal.acroformPlugin.acroFormDictionaryRoot.getString());
        }

        var fieldArray = fieldArray || scope.internal.acroformPlugin.acroFormDictionaryRoot.Kids;

        for (var i in fieldArray) {
            var key = i;
            var form = fieldArray[i];

            var oldRect = form.Rect;

            if (form.Rect) {
                form.Rect = calculateCoordinates.call(this, form.Rect);
            }

            // Start Writing the Object
            scope.internal.newObjectDeferredBegin(form.objId);

            var content = "";
            content += (form.objId + " 0 obj\n");

            content += ("<<\n" + form.getContent());

            form.Rect = oldRect;

            if (form.hasAppearanceStream && !form.appearanceStreamContent) {
                // Calculate Appearance
                var appearance = calculateAppearanceStream.call(this, form);
                content += "/AP << /N " + appearance + " >>\n";

                scope.internal.acroformPlugin.xForms.push(appearance);
            }

            // Assume AppearanceStreamContent is a Array with N,R,D (at least one of them!)
            if (form.appearanceStreamContent) {
                content += "/AP << ";
                // Iterate over N,R and D
                for (var k in form.appearanceStreamContent) {
                    var value = form.appearanceStreamContent[k];
                    content += ("/" + k + " ");
                    content += "<< ";
                    if (Object.keys(value).length >= 1 || Array.isArray(value)) {
                        // appearanceStream is an Array or Object!
                        for (var i in value) {
                            var obj = value[i];
                            if (typeof obj === 'function') {
                                // if Function is referenced, call it in order to get the FormXObject
                                obj = obj.call(this, form);
                            }
                            content += ("/" + i + " " + obj + " ");

                            // In case the XForm is already used, e.g. OffState of CheckBoxes, don't add it
                            if (!(scope.internal.acroformPlugin.xForms.indexOf(obj) >= 0))
                                scope.internal.acroformPlugin.xForms.push(obj);
                        }
                    } else {
                        var obj = value;
                        if (typeof obj === 'function') {
                            // if Function is referenced, call it in order to get the FormXObject
                            obj = obj.call(this, form);
                        }
                        content += ("/" + i + " " + obj + " \n");
                        if (!(scope.internal.acroformPlugin.xForms.indexOf(obj) >= 0))
                            scope.internal.acroformPlugin.xForms.push(obj);
                    }
                    content += " >>\n";
                }

                // appearance stream is a normal Object..
                content += (">>\n");
            }

            content += (">>\nendobj\n");

            scope.internal.out(content);

        }
        if (standardFields) {
            createXFormObjectCallback.call(this, scope.internal.acroformPlugin.xForms);
        }
    };

    var createXFormObjectCallback = function (fieldArray) {
        for (var i in fieldArray) {
            var key = i;
            var form = fieldArray[i];
            // Start Writing the Object
            scope.internal.newObjectDeferredBegin(form && form.objId);

            var content = "";
            content += form ? form.getString() : '';
            scope.internal.out(content);

            delete fieldArray[key];
        }
    };
    var initializeAcroForm = function () {
        if (this.internal !== undefined && (this.internal.acroformPlugin === undefined || this.internal.acroformPlugin.isInitialized === false)) {

            scope = this;

            AcroFormField.FieldNum = 0;
            this.internal.acroformPlugin = JSON.parse(JSON.stringify(acroformPluginTemplate));
            if (this.internal.acroformPlugin.acroFormDictionaryRoot) {
                //return;
                throw new Error("Exception while creating AcroformDictionary");
            }
            scaleFactor = scope.internal.scaleFactor;
            pageHeight = scope.internal.pageSize.height;

            // The Object Number of the AcroForm Dictionary
            scope.internal.acroformPlugin.acroFormDictionaryRoot = new AcroFormDictionary();

            // add Callback for creating the AcroForm Dictionary
            scope.internal.acroformPlugin.acroFormDictionaryRoot._eventID = scope.internal.events.subscribe('postPutResources', AcroFormDictionaryCallback);

            scope.internal.events.subscribe('buildDocument', annotReferenceCallback); //buildDocument

            // Register event, that is triggered when the DocumentCatalog is written, in order to add /AcroForm
            scope.internal.events.subscribe('putCatalog', putCatalogCallback);

            // Register event, that creates all Fields
            scope.internal.events.subscribe('postPutPages', createFieldCallback);
            
            scope.internal.acroformPlugin.isInitialized = true;
        }
    }
    

 // ### Handy Functions:

     var arrayToPdfArray = function (array) {
         if (Array.isArray(array)) {
             var content = ' [';
             for (var i in array) {
                 var element = array[i].toString();
                 content += element;
                 content += ((i < array.length - 1) ? ' ' : '');
             }
             content += ']';
    
             return content;
         }
     };
    
     var toPdfString = function (string) {
         string = string || "";
    
         // put Bracket at the Beginning of the String
         if (string.indexOf('(') !== 0) {
             string = '(' + string;
         }
         
         if (string.substring(string.length - 1) != ')') {
             string += ')';
         }
         return string;
     };

        // ##########################
         // Classes
        // ##########################

        var AcroFormPDFObject = function () {
            // The Object ID in the PDF Object Model
            // todo
            var _objId;
            Object.defineProperty(this, 'objId', {
                get: function () {
                    if (!_objId) {
                         _objId = scope.internal.newObjectDeferred();
                    }
                    if (!_objId) {
                        console.log("Couldn't create Object ID");
                    }
                    return _objId
                },
                configurable: false
            });
        };

        AcroFormPDFObject.prototype.toString = function () {
            return this.objId + " 0 R";
        };

        AcroFormPDFObject.prototype.getString = function () {
            var res = this.objId + " 0 obj\n<<";
            var content = this.getContent();

            res += content + ">>\n";
            if (this.stream) {
                res += "stream\n";
                res += this.stream;
                res += "endstream\n";
            }
            res += "endobj\n";
            return res;
        };

        AcroFormPDFObject.prototype.getContent = function () {
            /**
             * Prints out all enumerable Variables from the Object
             * @param fieldObject
             * @returns {string}
             */
            var createContentFromFieldObject = function (fieldObject) {
                var content = '';

                var keys = Object.keys(fieldObject).filter(function (key) {
                    return (key != 'content' && key != 'appearanceStreamContent' && key.substring(0, 1) != "_");
                });

                for (var i in keys) {
                    var key = keys[i];
                    var value = fieldObject[key];

                    /*if (key == 'Rect' && value) {
                     value = AcroForm.internal.calculateCoordinates.call(jsPDF.API.acroformPlugin.internal, value);
                     }*/

                    if (value) {
                        if (Array.isArray(value)) {
                            content += '/' + key + ' ' + arrayToPdfArray(value) + "\n";
                        } else if (value instanceof AcroFormPDFObject) {
                            // In case it is a reference to another PDFObject, take the referennce number
                            content += '/' + key + ' ' + value.objId + " 0 R" + "\n";
                        } else {
                            content += '/' + key + ' ' + value + '\n';
                        }
                    }
                }
                return content;
            };

            var object = "";

            object += createContentFromFieldObject(this);
            return object;
        };

        var AcroFormXObject = function () {
            AcroFormPDFObject.call(this);
            this.Type = "/XObject";
            this.Subtype = "/Form";
            this.FormType = 1;
            this.BBox;
            this.Matrix;
            this.Resources = "2 0 R";
            this.PieceInfo;
            var _stream;
            Object.defineProperty(this, 'Length', {
                enumerable: true,
                get: function () {
                    return (_stream !== undefined) ? _stream.length : 0;
                }
            });
            Object.defineProperty(this, 'stream', {
                enumerable: false,
                set: function (val) {
                    _stream = val;
                },
                get: function () {
                    if (_stream) {
                        return _stream;
                    } else {
                        return null;
                    }
                }
            });
        };

        inherit(AcroFormXObject, AcroFormPDFObject);
        // ##### The Objects, the User can Create:
        
        var AcroFormDictionary = function () {
            AcroFormPDFObject.call(this);
            var _Kids = [];
            Object.defineProperty(this, 'Kids', {
                enumerable: false,
                configurable: true,
                get: function () {
                    if (_Kids.length > 0) {
                        return _Kids;
                    } else {
                        return;
                    }
                }
            });
            Object.defineProperty(this, 'Fields', {
                enumerable: true,
                configurable: true,
                get: function () {
                    return _Kids;
                }
            });
            // Default Appearance
            this.DA;
        };

        inherit(AcroFormDictionary, AcroFormPDFObject);


        // The Field Object contains the Variables, that every Field needs
        // Rectangle for Appearance: lower_left_X, lower_left_Y, width, height
        var AcroFormField = function () {
            'use strict';
            AcroFormPDFObject.call(this);

            var _Rect;
            Object.defineProperty(this, 'Rect', {
                enumerable: true,
                configurable: false,
                get: function () {
                    if (!_Rect) {
                        return;
                    }
                    var tmp = _Rect;
                    //var calculatedRes = AcroForm.internal.calculateCoordinates(_Rect); // do later!
                    return tmp
                },
                set: function (val) {
                    _Rect = val;
                }
            });

            var _FT = "";
            Object.defineProperty(this, 'FT', {
                enumerable: true,
                set: function (val) {
                    _FT = val
                },
                get: function () {
                    return _FT
                }
            });
            /**
             * The Partial name of the Field Object.
             * It has to be unique.
             */
            var _T;

            Object.defineProperty(this, 'T', {
                enumerable: true,
                configurable: false,
                set: function (val) {
                    _T = val;
                },
                get: function () {
                    if (!_T || _T.length < 1) {
                        if (this instanceof AcroFormChildClass) {
                            // In case of a Child from a Radio´Group, you don't need a FieldName!!!
                            return;
                        }
                        return "(FieldObject" + (AcroFormField.FieldNum++) + ")";
                    }
                    if (_T.substring(0, 1) == "(" && _T.substring(_T.length - 1)) {
                        return _T;
                    }
                    return "(" + _T + ")";
                }
            });

            var _DA;
            // Defines the default appearance (Needed for variable Text)
            Object.defineProperty(this, 'DA', {
                enumerable: true,
                get: function () {
                    if (!_DA) {
                        return;
                    }
                    return '(' + _DA + ')'
                },
                set: function (val) {
                    _DA = val
                }
            });

            var _DV;
            // Defines the default value
            Object.defineProperty(this, 'DV', {
                enumerable: true,
                configurable: true,
                get: function () {
                    if (!_DV) {
                        return;
                    }
                    return _DV
                },
                set: function (val) {
                    _DV = val
                }
            });
            
            var _V;
            // Defines the default value
            Object.defineProperty(this, 'V', {
                enumerable: true,
                configurable: true,
                get: function () {
                    if (!_V) {
                        return;
                    }
                    return _V
                },
                set: function (val) {
                    _V = val
                }
            });

            //this.Type = "/Annot";
            //this.Subtype = "/Widget";
            Object.defineProperty(this, 'Type', {
                enumerable: true,
                get: function () {
                    return (this.hasAnnotation) ? "/Annot" : null;
                }
            });

            Object.defineProperty(this, 'Subtype', {
                enumerable: true,
                get: function () {
                    return (this.hasAnnotation) ? "/Widget" : null;
                }
            });

            /**
             *
             * @type {Array}
             */
            this.BG;

            Object.defineProperty(this, 'hasAnnotation', {
                enumerable: false,
                get: function () {
                    if (this.Rect || this.BC || this.BG) {
                        return true
                    }
                    return false;
                }
            });

            Object.defineProperty(this, 'hasAppearanceStream', {
                enumerable: false,
                configurable: true,
                writable: true
            });

            Object.defineProperty(this, 'page', {
                enumerable: false,
                configurable: true,
                writable: true
            });
        };

        inherit(AcroFormField, AcroFormPDFObject);
        
        var AcroFormChoiceField = function () {
            AcroFormField.call(this);
            // Field Type = Choice Field
            this.FT = "/Ch";
            // options
            this.Opt = [];
            this.V = '()';
            // Top Index
            this.TI = 0;
            /**
             * Defines, whether the
             * @type {boolean}
             */

            var _combo = false;

            Object.defineProperty(this, 'combo', {
                enumerable: false,
                get: function () {
                    return _combo
                },
                set: function (val) {
                    _combo = val
                }
            });
            /**
             * Defines, whether the Choice Field is an Edit Field.
             * An Edit Field is automatically an Combo Field.
             */
            Object.defineProperty(this, 'edit', {
                enumerable: true,
                set: function (val) {
                    if (val == true) {
                        this._edit = true;
                        // ComboBox has to be true
                        this.combo = true;
                    } else {
                        this._edit = false;
                    }
                },
                get: function () {
                    if (!this._edit) {
                        return false;
                    }
                    return this._edit;
                },
                configurable: false
            });
            this.hasAppearanceStream = true;
        };
        inherit(AcroFormChoiceField, AcroFormField);
        
        var AcroFormListBox = function () {
            AcroFormChoiceField.call(this);
            this.combo = false;
        };
        inherit(AcroFormListBox, AcroFormChoiceField);

        var AcroFormComboBox = function () {
            AcroFormListBox.call(this);
            this.combo = true;
        };
        inherit(AcroFormComboBox, AcroFormListBox);

        var AcroFormEditBox = function () {
            AcroFormComboBox.call(this);
            this.edit = true;
        };
        inherit(AcroFormEditBox, AcroFormComboBox);
        

        var AcroFormButton = function () {
            AcroFormField.call(this);
            this.FT = "/Btn";
            //this.hasAnnotation = true;
        };
        inherit(AcroFormButton, AcroFormField);
        
        var AcroFormPushButton = function () {
            AcroFormButton.call(this);

            var _pushbutton = true;
            Object.defineProperty(this, 'pushbutton', {
                enumerable: false,
                get: function () {
                    return _pushbutton;
                },
                set: function (val) {
                    _pushbutton = val;
                }
            });
            
        };
        inherit(AcroFormPushButton, AcroFormButton);

        var AcroFormRadioButton = function () {
            AcroFormButton.call(this);
            
            var _radio = true;
            Object.defineProperty(this, 'radio', {
                enumerable: false,
                get: function () {
                    return _radio;
                },
                set: function (val) {
                    _radio = val;
                }
            });
            
            var _Kids = [];
            Object.defineProperty(this, 'Kids', {
                enumerable: true,
                get: function () {
                    if (_Kids.length > 0) {
                        return _Kids;
                    }
                }
            });

            Object.defineProperty(this, '__Kids', {
                get: function () {
                    return _Kids;
                }
            });

            var _noToggleToOff;

            Object.defineProperty(this, 'noToggleToOff', {
                enumerable: false,
                get: function () {
                    return _noToggleToOff
                },
                set: function (val) {
                    _noToggleToOff = val
                }
            });


            //this.hasAnnotation = false;
        };
        inherit(AcroFormRadioButton, AcroFormButton);
        

        /*
         * The Child classs of a RadioButton (the radioGroup)
         * -> The single Buttons
         */
        var AcroFormChildClass = function (parent, name) {
            AcroFormField.call(this);
            this.Parent = parent;

            // todo: set AppearanceType as variable that can be set from the outside...
            this._AppearanceType = AcroFormAppearance.RadioButton.Circle; // The Default appearanceType is the Circle
            this.appearanceStreamContent = this._AppearanceType.createAppearanceStream(name);

            // Set Print in the Annot Flag
            this.F = setBitPosition(this.F, 3, 1);

            // Set AppearanceCharacteristicsDictionary with default appearance if field is not interacting with user
            this.MK = this._AppearanceType.createMK(); // (8) -> Cross, (1)-> Circle, ()-> nothing

            // Default Appearance is Off
            this.AS = "/Off";// + name;

            this._Name = name;
        };
        inherit(AcroFormChildClass, AcroFormField);

        AcroFormRadioButton.prototype.setAppearance = function (appearance) {
            if (!('createAppearanceStream' in appearance && 'createMK' in appearance)) {
                console.log("Couldn't assign Appearance to RadioButton. Appearance was Invalid!");
                return;
            }
            for (var i in this.__Kids) {
                var child = this.__Kids[i];

                child.appearanceStreamContent = appearance.createAppearanceStream(child._Name);
                child.MK = appearance.createMK();
            }
        };

        AcroFormRadioButton.prototype.createOption = function (name) {
            var parent = this;
            var kidCount = this.__Kids.length;

            // Create new Child for RadioGroup
            var child = new AcroFormChildClass(parent, name);
            // Add to Parent
            this.__Kids.push(child);

            jsPDFAPI.addField(child);

            return child;
        };
        

        var AcroFormCheckBox = function () {
            AcroFormButton.call(this);
            this.appearanceStreamContent = AcroFormAppearance.CheckBox.createAppearanceStream();
            this.MK = AcroFormAppearance.CheckBox.createMK();
            this.AS = "/On";
            this.V = "/On";
        };
        inherit(AcroFormCheckBox, AcroFormButton);

        var AcroFormTextField = function () {
            AcroFormField.call(this);
            this.DA = AcroFormAppearance.createDefaultAppearanceStream();
            this.F = 4;
            var _V;
            Object.defineProperty(this, 'V', {
                get: function () {
                    if (_V) {
                        return toPdfString(_V);
                    } else {
                        return _V;
                    }
                },
                enumerable: true,
                set: function (val) {
                    _V = val
                }
            });

            var _DV;
            Object.defineProperty(this, 'DV', {
                get: function () {
                    if (_DV) {
                        return toPdfString(_DV);
                    } else {
                        return _DV;
                    }
                },
                enumerable: true,
                set: function (val) {
                    _DV = val
                }
            });

            var _multiline = false;
            Object.defineProperty(this, 'multiline', {
                enumerable: false,
                get: function () {
                    return _multiline
                },
                set: function (val) {
                    _multiline = val;
                }
            });

            /**
             * For PDF 1.4
             * @type {boolean}
             */
            var _fileSelect = false;
            Object.defineProperty(this, 'fileSelect', {
                enumerable: false,
                get: function () {
                    return _fileSelect
                },
                set: function (val) {
                    _fileSelect = val;
                }
            });
            /**
             * For PDF 1.4
             * @type {boolean}
             */
            var _doNotSpellCheck = false;
            Object.defineProperty(this, 'doNotSpellCheck', {
                enumerable: false,
                get: function () {
                    return _doNotSpellCheck
                },
                set: function (val) {
                    _doNotSpellCheck = val;
                }
            });
            /**
             * For PDF 1.4
             * @type {boolean}
             */
            var _doNotScroll = false;
            Object.defineProperty(this, 'doNotScroll', {
                enumerable: false,
                get: function () {
                    return _doNotScroll
                },
                set: function (val) {
                    _doNotScroll = val;
                }
            });

            var _MaxLen = false;
            Object.defineProperty(this, 'MaxLen', {
                enumerable: true,
                get: function () {
                    return _MaxLen;
                },
                set: function (val) {
                    _MaxLen = val;
                }
            });

            Object.defineProperty(this, 'hasAppearanceStream', {
                enumerable: false,
                get: function () {
                    return (this.V || this.DV);
                }
            });

        };
        inherit(AcroFormTextField, AcroFormField);

        var AcroFormPasswordField = function () {
            AcroFormTextField.call(this);

            var _password = true;
            Object.defineProperty(this, 'password', {
                enumerable: false,
                get: function () {
                    return _password
                },
                set: function (val) {
                    _password = val;
                }
            });
        };
        inherit(AcroFormPasswordField, AcroFormTextField);
        

     // Contains Methods for creating standard appearances
    var AcroFormAppearance = {
         CheckBox: {
             createAppearanceStream: function () {
                 var appearance = {
                     N: {
                         On: AcroFormAppearance.CheckBox.YesNormal
                     },
                     D: {
                         On: AcroFormAppearance.CheckBox.YesPushDown,
                         Off: AcroFormAppearance.CheckBox.OffPushDown
                     }
                 };

                 return appearance;
             },
             /**
              * If any other icons are needed, the number between the brackets can be changed
              * @returns {string}
              */
             createMK: function () {
                 // 3-> Hook
                 return "<< /CA (3)>>";
             },
             /**
              * Returns the standard On Appearance for a CheckBox
              * @returns {AcroFormXObject}
              */
             YesPushDown: function (formObject) {
                 var xobj = createFormXObject(formObject);
                 var stream = "";
                 var zapfDingbats = "F13"; //scope.internal.getFont("zapfdingbats").id || "F13";
                 // F13 is ZapfDingbats (Symbolic)
                 formObject.Q = 1; // set text-alignment as centered
                 var calcRes = calculateX(formObject, "3", "ZapfDingbats", 50);
                 stream += "0.749023 g\n";
                 stream += "0 0 " + AcroFormAppearance.internal.getWidth(formObject).toFixed(2) + " " + AcroFormAppearance.internal.getHeight(formObject).toFixed(2) + " re\n";
                 stream += "f\n";
                 stream += "BMC\n";
                 stream += "q\n";
                 stream += "0 0 1 rg\n"
                 stream += "/" + zapfDingbats + " " + calcRes.fontSize.toFixed(2) + " Tf 0 g\n";
                 stream += "BT\n";
                 stream += calcRes.text;
                 stream += "ET\n"
                 stream += "Q\n";
                 stream += "EMC\n";
                 xobj.stream = stream;
                 return xobj;
             },

             YesNormal: function (formObject) {
                 var xobj = createFormXObject(formObject);
                 var stream = "";
                 formObject.Q = 1; // set text-alignment as centered
                 var calcRes = calculateX(formObject, "3", "ZapfDingbats", AcroFormAppearance.internal.getHeight(formObject) * 0.9);
                 stream += "1 g\n";
                 stream += "0 0 " + (AcroFormAppearance.internal.getWidth(formObject)).toFixed(2) + " " + (AcroFormAppearance.internal.getHeight(formObject)).toFixed(2) + " re\n";
                 stream += "f\n";
                 stream += "q\n";
                 stream += "0 0 1 rg\n";
                 stream += "0 0 " + (AcroFormAppearance.internal.getWidth(formObject) - 1).toFixed(2) + " " + (AcroFormAppearance.internal.getHeight(formObject) - 1).toFixed(2) + " re\n";
                 stream += "W\n";
                 stream += "n\n";
                 stream += "0 g\n";
                 stream += "BT\n";
                 stream += "/F13 " + calcRes.fontSize.toFixed(2) + " Tf 0 g\n";
                 stream += calcRes.text;
                 stream += "ET\n";
                 stream += "Q\n";
                 xobj.stream = stream;
                 return xobj;
             },

             /**
              * Returns the standard Off Appearance for a CheckBox
              * @returns {AcroFormXObject}
              */
             OffPushDown: function (formObject) {
                 var xobj = createFormXObject(formObject);
                 var stream = "";
                 stream += "0.749023 g\n";
                 stream += "0 0 " + AcroFormAppearance.internal.getWidth(formObject).toFixed(2) + " " + AcroFormAppearance.internal.getHeight(formObject).toFixed(2) + " re\n";
                 stream += "f\n";
                 xobj.stream = stream;
                 return xobj;
             }
         },

         RadioButton: {
             Circle: {
                 createAppearanceStream: function (name) {
                     var appearanceStreamContent = {
                         D: {
                             'Off': AcroFormAppearance.RadioButton.Circle.OffPushDown
                         },
                         N: {}
                     };
                     appearanceStreamContent.N[name] = AcroFormAppearance.RadioButton.Circle.YesNormal;
                     appearanceStreamContent.D[name] = AcroFormAppearance.RadioButton.Circle.YesPushDown;
                     return appearanceStreamContent;
                 },
                 createMK: function () {
                     return "<< /CA (l)>>";
                 },

                 YesNormal: function (formObject) {
                     var xobj =  createFormXObject(formObject);
                     var stream = "";
                     // Make the Radius of the Circle relative to min(height, width) of formObject
                     var DotRadius = (AcroFormAppearance.internal.getWidth(formObject) <= AcroFormAppearance.internal.getHeight(formObject)) ?
                     AcroFormAppearance.internal.getWidth(formObject) / 4 : AcroFormAppearance.internal.getHeight(formObject) / 4;
                     // The Borderpadding...
                     DotRadius *= 0.9;
                     var c = AcroFormAppearance.internal.Bezier_C;
                     /*
                      The Following is a Circle created with Bezier-Curves.
                      */
                     stream += "q\n";
                     stream += "1 0 0 1 " + AcroFormAppearance.internal.getWidth(formObject) / 2 + " " + AcroFormAppearance.internal.getHeight(formObject) / 2 + " cm\n";
                     stream += DotRadius + " 0 m\n";
                     stream += DotRadius + " " + DotRadius * c + " " + DotRadius * c + " " + DotRadius + " 0 " + DotRadius + " c\n";
                     stream += "-" + DotRadius * c + " " + DotRadius + " -" + DotRadius + " " + DotRadius * c + " -" + DotRadius + " 0 c\n";
                     stream += "-" + DotRadius + " -" + DotRadius * c + " -" + DotRadius * c + " -" + DotRadius + " 0 -" + DotRadius + " c\n";
                     stream += DotRadius * c + " -" + DotRadius + " " + DotRadius + " -" + DotRadius * c + " " + DotRadius + " 0 c\n";
                     stream += "f\n";
                     stream += "Q\n";
                     xobj.stream = stream;
                     return xobj;
                 },
                 YesPushDown: function (formObject) {
                     var xobj = createFormXObject(formObject);
                     var stream = "";
                     var DotRadius = (AcroFormAppearance.internal.getWidth(formObject) <= AcroFormAppearance.internal.getHeight(formObject)) ?
                     AcroFormAppearance.internal.getWidth(formObject) / 4 : AcroFormAppearance.internal.getHeight(formObject) / 4;
                     // The Borderpadding...
                     DotRadius *= 0.9;
                     // Save results for later use; no need to waste processor ticks on doing math
                     var k = DotRadius * 2;
                     // var c = AcroFormAppearance.internal.Bezier_C;
                     var kc = k * AcroFormAppearance.internal.Bezier_C;
                     var dc = DotRadius * AcroFormAppearance.internal.Bezier_C;

                     stream += "0.749023 g\n";
                     stream += "q\n";
                     stream += "1 0 0 1 " + (AcroFormAppearance.internal.getWidth(formObject) / 2).toFixed(2) + " " + (AcroFormAppearance.internal.getHeight(formObject) / 2).toFixed(2) + " cm\n";
                     stream += k + " 0 m\n";
                     stream += k + " " + kc + " " + kc + " " + k + " 0 " + k + " c\n";
                     stream += "-" + kc + " " + k + " -" + k + " " + kc + " -" + k + " 0 c\n";
                     stream += "-" + k + " -" + kc + " -" + kc + " -" + k + " 0 -" + k + " c\n";
                     stream += kc + " -" + k + " " + k + " -" + kc + " " + k + " 0 c\n";
                     stream += "f\n";
                     stream += "Q\n";
                     stream += "0 g\n";
                     stream += "q\n";
                     stream += "1 0 0 1 " + (AcroFormAppearance.internal.getWidth(formObject) / 2).toFixed(2) + " " + (AcroFormAppearance.internal.getHeight(formObject) / 2).toFixed(2) + " cm\n";
                     stream += DotRadius + " 0 m\n";
                     stream += "" + DotRadius + " " + dc + " " + dc + " " + DotRadius + " 0 " + DotRadius + " c\n";
                     stream += "-" + dc + " " + DotRadius + " -" + DotRadius + " " + dc + " -" + DotRadius + " 0 c\n";
                     stream += "-" + DotRadius + " -" + dc + " -" + dc + " -" + DotRadius + " 0 -" + DotRadius + " c\n";
                     stream += dc + " -" + DotRadius + " " + DotRadius + " -" + dc + " " + DotRadius + " 0 c\n";
                     stream += "f\n";
                     stream += "Q\n";
                     xobj.stream = stream;
                     return xobj;
                 },
                 OffPushDown: function (formObject) {
                     var xobj = createFormXObject(formObject);
                     var stream = "";
                     var DotRadius = (AcroFormAppearance.internal.getWidth(formObject) <= AcroFormAppearance.internal.getHeight(formObject)) ?
                     AcroFormAppearance.internal.getWidth(formObject) / 4 : AcroFormAppearance.internal.getHeight(formObject) / 4;
                     // The Borderpadding...
                     DotRadius *= 0.9;
                     // Save results for later use; no need to waste processor ticks on doing math
                     var k = DotRadius * 2;
                     // var c = AcroFormAppearance.internal.Bezier_C;
                     var kc = k * AcroFormAppearance.internal.Bezier_C;

                     stream += "0.749023 g\n";
                     stream += "q\n";
                     stream += "1 0 0 1 " + (AcroFormAppearance.internal.getWidth(formObject) / 2).toFixed(2) + " " + (AcroFormAppearance.internal.getHeight(formObject) / 2).toFixed(2) + " cm\n";
                     stream += k + " 0 m\n";
                     stream += k + " " + kc + " " + kc + " " + k + " 0 " + k + " c\n";
                     stream += "-" + kc + " " + k + " -" + k + " " + kc + " -" + k + " 0 c\n";
                     stream += "-" + k + " -" + kc + " -" + kc + " -" + k + " 0 -" + k + " c\n";
                     stream += kc + " -" + k + " " + k + " -" + kc + " " + k + " 0 c\n";
                     stream += "f\n";
                     stream += "Q\n";
                     xobj.stream = stream;
                     return xobj;
                 },
             },

             Cross: {
                 /**
                  * Creates the Actual AppearanceDictionary-References
                  * @param name
                  * @returns
                  */
                 createAppearanceStream: function (name) {
                     var appearanceStreamContent = {
                         D: {
                             'Off': AcroFormAppearance.RadioButton.Cross.OffPushDown
                         },
                         N: {}
                     };
                     appearanceStreamContent.N[name] = AcroFormAppearance.RadioButton.Cross.YesNormal;
                     appearanceStreamContent.D[name] = AcroFormAppearance.RadioButton.Cross.YesPushDown;
                     return appearanceStreamContent;
                 },
                 createMK: function () {
                     return "<< /CA (8)>>";
                 },


                 YesNormal: function (formObject) {
                     var xobj = createFormXObject(formObject);
                     var stream = "";
                     var cross = AcroFormAppearance.internal.calculateCross(formObject);
                     stream += "q\n";
                     stream += "1 1 " + (AcroFormAppearance.internal.getWidth(formObject) - 2).toFixed(2) + " " + (AcroFormAppearance.internal.getHeight(formObject) - 2).toFixed(2) + " re\n";
                     stream += "W\n";
                     stream += "n\n";
                     stream += cross.x1.x.toFixed(2) + " " + cross.x1.y.toFixed(2) + " m\n";
                     stream += cross.x2.x.toFixed(2) + " " + cross.x2.y.toFixed(2) + " l\n";
                     stream += cross.x4.x.toFixed(2) + " " + cross.x4.y.toFixed(2) + " m\n";
                     stream += cross.x3.x.toFixed(2) + " " + cross.x3.y.toFixed(2) + " l\n";
                     stream += "s\n";
                     stream += "Q\n";
                     xobj.stream = stream;
                     return xobj;
                 },
                 YesPushDown: function (formObject) {
                     var xobj = createFormXObject(formObject);
                     var cross = AcroFormAppearance.internal.calculateCross(formObject);
                     var stream = "";
                     stream += "0.749023 g\n";
                     stream += "0 0 " + (AcroFormAppearance.internal.getWidth(formObject)).toFixed(2) + " " + (AcroFormAppearance.internal.getHeight(formObject)).toFixed(2) + " re\n";
                     stream += "f\n";
                     stream += "q\n";
                     stream += "1 1 " + (AcroFormAppearance.internal.getWidth(formObject) - 2).toFixed(2) + " " + (AcroFormAppearance.internal.getHeight(formObject) - 2).toFixed(2) + " re\n";
                     stream += "W\n";
                     stream += "n\n";
                     stream += cross.x1.x.toFixed(2) + " " + cross.x1.y.toFixed(2) + " m\n";
                     stream += cross.x2.x.toFixed(2) + " " + cross.x2.y.toFixed(2) + " l\n";
                     stream += cross.x4.x.toFixed(2) + " " + cross.x4.y.toFixed(2) + " m\n";
                     stream += cross.x3.x.toFixed(2) + " " + cross.x3.y.toFixed(2) + " l\n";
                     stream += "s\n";
                     stream += "Q\n";
                     xobj.stream = stream;
                     return xobj;
                 },
                 OffPushDown: function (formObject) {
                     var xobj = createFormXObject(formObject);
                     var stream = "";
                     stream += "0.749023 g\n";
                     stream += "0 0 " + (AcroFormAppearance.internal.getWidth(formObject)).toFixed(2) + " " + (AcroFormAppearance.internal.getHeight(formObject)).toFixed(2) + " re\n";
                     stream += "f\n";
                     xobj.stream = stream;
                     return xobj;
                 }
             },
         },

         /**
          * Returns the standard Appearance
          * @returns {AcroFormXObject}
          */
         createDefaultAppearanceStream: function (formObject) {
             var stream = "";
             // Set Helvetica to Standard Font (size: auto)
             // Color: Black
             stream += "/Helv 0 Tf 0 g";
             return stream;
         }
     };

     AcroFormAppearance.internal = {
         Bezier_C: 0.551915024494,

         calculateCross: function (formObject) {
             var min = function (x, y) {
                 return (x > y) ? y : x;
             };

             var width = AcroFormAppearance.internal.getWidth(formObject);
             var height = AcroFormAppearance.internal.getHeight(formObject);
             var a = min(width, height);
             var crossSize = a;
             var borderPadding = 2; // The Padding in px


             var cross = {
                 x1: { // upperLeft
                     x: (width - a) / 2,
                     y: ((height - a) / 2) + a,//height - borderPadding
                 },
                 x2: { // lowerRight
                     x: ((width - a) / 2) + a,
                     y: ((height - a) / 2)//borderPadding
                 },
                 x3: { // lowerLeft
                     x: (width - a) / 2,
                     y: ((height - a) / 2)//borderPadding
                 },
                 x4: { // upperRight
                     x: ((width - a) / 2) + a,
                     y: ((height - a) / 2) + a,//height - borderPadding
                 }
             };

             return cross;
         },
     };
     AcroFormAppearance.internal.getWidth = function (formObject) {
         return scale(formObject.Rect[2]);//(formObject.Rect[2] - formObject.Rect[0]) || 0;
     };
     AcroFormAppearance.internal.getHeight = function (formObject) {
         return scale(formObject.Rect[3]);//(formObject.Rect[1] - formObject.Rect[3]) || 0;
     };

    // Public:

    jsPDFAPI.addField = function (fieldObject) {
        initializeAcroForm.call(this);
        //var opt = parseOptions(fieldObject);
        if (fieldObject instanceof AcroFormTextField) {
            this.addTextField.call(this, fieldObject);
        } else if (fieldObject instanceof AcroFormChoiceField) {
            this.addChoiceField.call(this, fieldObject);
        } else if (fieldObject instanceof AcroFormButton) {
            this.addButton.call(this, fieldObject);
        } else if (fieldObject instanceof AcroFormChildClass) {
            putForm.call(this, fieldObject);
        } else if (fieldObject) {
            // try to put..
            putForm.call(this, fieldObject);
        }
        fieldObject.page = scope.internal.getCurrentPageInfo().pageNumber;
        return this;
    };
    


        /**
         * Button
         * FT = Btn
         */
        jsPDFAPI.addButton = function (opts) {
            initializeAcroForm.call(this);
            var options = opts || new AcroFormField();

            options.FT = '/Btn';
            options.Ff = calculateFlagsOnOptions(options.Ff, opts, scope.internal.getPDFVersion());

            putForm.call(this, options);

        };

        jsPDFAPI.addTextField = function (opts) {
            initializeAcroForm.call(this);
            var options = opts || new AcroFormField();

            options.FT = '/Tx';

            options.Ff = calculateFlagsOnOptions(options.Ff, opts, scope.internal.getPDFVersion());

            // Add field
            putForm.call(this, options);
        };
        
        jsPDFAPI.addChoiceField = function (opts) {
            initializeAcroForm.call(this);
            var options = opts || new AcroFormField();

            options.FT = '/Ch';

            options.Ff = calculateFlagsOnOptions(options.Ff, opts, scope.internal.getPDFVersion());
            //options.hasAnnotation = true;

            // Add field
            putForm.call(this, options);
        };
        
        if (typeof globalObj == "object") {
            globalObj["ChoiceField"] = AcroFormChoiceField;
            globalObj["ListBox"] = AcroFormListBox;
            globalObj["ComboBox"] = AcroFormComboBox;
            globalObj["EditBox"] = AcroFormEditBox;
            globalObj["Button"] = AcroFormButton;
            globalObj["PushButton"] = AcroFormPushButton;
            globalObj["RadioButton"] = AcroFormRadioButton;
            globalObj["CheckBox"] = AcroFormCheckBox;
            globalObj["TextField"] = AcroFormTextField;
            globalObj["PasswordField"] = AcroFormPasswordField;
            
            //backwardsCompatibility
            globalObj["AcroForm"] = {Appearance: AcroFormAppearance};
        }
})(jsPDF.API, (typeof window !== "undefined" && window || typeof global !== "undefined" && global));
