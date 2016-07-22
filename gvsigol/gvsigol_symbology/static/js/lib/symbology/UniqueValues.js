/**
 * gvSIG Online.
 * Copyright (C) 2007-2015 gvSIG Association.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

/**
 * @author: Javier Rodrigo <jrodrigo@scolab.es>
 */
 
 
var UniqueValues = function(featureType, layerName, symbologyUtils, previewUrl) {
	this.selected = null;
	this.featureType = featureType;
	this.layerName = layerName;
	this.previewUrl = previewUrl;
	this.symbologyUtils = symbologyUtils;
	this.rules = new Array();
};

UniqueValues.prototype.getRules = function() {
	return this.rules;
};

UniqueValues.prototype.addRule = function(rule) {
	return this.rules.push(rule);
};

UniqueValues.prototype.load = function(values) {
	$('#rules').empty();
	this.rules.splice(0, this.rules.length);
	for (var i=0; i<values.length; i++) {
		var ruleName = "rule_" + 1;
		var ruleTitle = values[i];
		var rule = new Rule(i, ruleName, ruleTitle, null, this.symbologyUtils);
		$('#rules').append(rule.getTableUI());
		rule.registerEvents();
		rule.addSymbolizer();
		rule.preview();
		this.addRule(rule);
	}
};

UniqueValues.prototype.refreshMap = function() {
	this.symbologyUtils.updateMap(this.rule, this.layerName);
};