gvsigolETL.View = draw2d.Canvas.extend({
	
	init:function(id)
    {
        this._super(id);
		
        this.setScrollArea("#"+id);
                
	},

    /**
     * @method
     * Called if the user drop the droppedDomNode onto the canvas.
     * 
     * Draw2D use the jQuery draggable/droppable lib. Please inspect
     * http://jqueryui.com/demos/droppable/ for further information.
     * 
     * @param {HTMLElement} droppedDomNode The dropped DOM element.
     * @param {Number} x the x coordinate of the drop
     * @param {Number} y the y coordinate of the drop
     **/
    onDrop : function(droppedDomNode, x, y)
    {
    
        var type = $(droppedDomNode).data("shape");
        
        var figure = eval("new "+type+"();");
        
        figure.addEntity("id");
        
        // create a command for the undo/redo support
        var command = new draw2d.command.CommandAdd(this, figure, x, y);
        this.getCommandStack().execute(command);

    }
        
});

