$( document ).ready(function() {
 
    $(".resource").each(function(index){
      var element = this;
      if ($(this).text() && $(this).text().substr(0,4) == 'http') {
        $.get('http://preflabel.org/api/v1/label/'+encodeURIComponent($(element).text())+"?callback=?", function(data){
          updateLabel(data,element);
        }).fail(function(){
          updateLabel($(element).text(),element);
          console.log("error");
        });
      } 
    });
    
    function updateLabel(label,element){
      var anchor = $("<a></a>");
      
      anchor.append(label);
      anchor.attr('href','/?uri='+$(element).text());
      
      $(element).html(anchor);
      
    }
  
});