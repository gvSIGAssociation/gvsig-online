// declare the namespace for this example
var gvsigolETL = {};

gvsigolETL.Application = Class.extend(
{
    NAME : "gvsigolETL.Application", 

    /**
     * @constructor
     * 
     * @param {String} canvasId the id of the DOM element to use as paint container
     */
    init : function()
    {
	      this.view    = new gvsigolETL.View("canvas-etl");
          this.toolbar = new gvsigolETL.Toolbar("toolbar-etl",  this.view );
    }
    


});
