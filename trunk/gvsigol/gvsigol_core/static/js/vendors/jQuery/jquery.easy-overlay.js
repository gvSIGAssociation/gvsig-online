(function( $ ){
	$.fn.overlay = function() {
    	var $t = $(this);
		
		if($t.length <= 0) return;
		
	  	var vzIndex;
	  	if($t.css('z-index') == "auto") vzIndex = "99999";
	  	else vzIndex = parseFloat($t.css('z-index')) + 1;
		
		if( !$("#jqueryEasyOverlayDiv").length ) {
			var innerDiv = document.createElement('div');
			$(innerDiv).css({ position: "absolute"}).attr("id", "jqueryOverlayLoad").html("<i class='fa fa-spin fa-spinner fa-2x'></i>&nbsp;");
			
			var div = document.createElement('div');	
			$(div).css({
				display: "none",
				position: "absolute",
				background: "#eee"
			}).attr('id',"jqueryEasyOverlayDiv").append(innerDiv);
			
			$("body").append(div);
		}
		
		
		
	  	$("#jqueryEasyOverlayDiv").css({
			opacity : 0.5,
		  	zIndex  : vzIndex,
		  	top     :  $t.offset().top,
		  	left    : $t.offset().left,
		  	width   : $t.outerWidth(),
		  	height  : $t.outerHeight()
		});
		
		var topOverlay = (($t.height()/2)-24);
		if(topOverlay < 0) topOverlay = 0;
		$("#jqueryOverlayLoad").css({
			top  : topOverlay,
		  	left : (($t.width()/2)-24)
		});
		
		$("#jqueryEasyOverlayDiv").fadeIn();
   	}; 
})(jQuery);

(function( $ ){
	$.fn.overlayout = function() {
		if( $("#jqueryEasyOverlayDiv").length ) $("#jqueryEasyOverlayDiv").fadeOut();
		
   }; 
})(jQuery);

(function( $ ){
	$.overlayout = function() {
		if( $("#jqueryEasyOverlayDiv").length ) $("#jqueryEasyOverlayDiv").fadeOut();
		
   }; 
})(jQuery);