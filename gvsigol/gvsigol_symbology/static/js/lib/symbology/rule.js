var Rule = function() {
	if ( !(this instanceof Rule) ) 
		return new Rule();
	
	this.id = ruleCount;
	this.name = "";
	this.description = "";
	this.preview = null;
	
	ruleCount++;
};