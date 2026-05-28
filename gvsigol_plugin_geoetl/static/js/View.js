gvsigolETL.View = draw2d.Canvas.extend({
	
	init:function(id)
    {
        this._super(id);
		
        this.setScrollArea("#canvas-parent");
                
	},

    /**
     * draw2d usa clientX/clientY (viewport) pero el método por defecto devuelve
     * offset() del canvas (documento). Hay que usar el rect del contenedor de
     * scroll (#canvas-parent), que es el mismo sistema de coordenadas que el
     * scrollTop que se compensa en fromDocumentToCanvasCoordinate.
     */
    getAbsoluteX: function()
    {
        return this.getScrollArea()[0].getBoundingClientRect().left;
    },

    getAbsoluteY: function()
    {
        return this.getScrollArea()[0].getBoundingClientRect().top;
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

