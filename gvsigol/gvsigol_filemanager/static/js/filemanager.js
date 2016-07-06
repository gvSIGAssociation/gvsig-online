var Filemanager = {
  show: function(id, url) {
    var doc = document;
    var filemanagerWindow = window.open(url, id, 'height=480,width=640,resizable=yes');
    filemanagerWindow.focus();

    window.filemanagerCallback = function(url) {
      doc.querySelector("input[id="+id+"]").value = url;
    }
  },
  select: function(url) {
    window.close();
    window.opener.filemanagerCallback(url);
  }
};
