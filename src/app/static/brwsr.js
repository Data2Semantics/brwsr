$( document ).ready(function() {
 
    $(".resource").each(function(index){
      var element = this;
      var element_text = $(this).text();
      if (element_text && element_text.substr(0,4) == 'http') {
        $.get('http://preflabel.org/api/v1/label/'+encodeURIComponent($(element).text())+"?callback=?", function(data){
          updateLabel(data,element);
        }).fail(function(){
          updateLabel(element_text,element);
        });
      } 
    });
    
    $(".literal").each(function(index){
        var element = this;
        var element_text = $(this).text();
        if (element_text.length > 50 ) {

              var span = $('<span></span>');

              span.text(element_text.substr(0,200) + '...');
              var icon = $('<span class="glyphicon glyphicon-play" aria-hidden="true"></span>');
              span.append(icon);
              icon.on('click', function(e){
                  span.text(element_text);
              });
              $(element).html(span);
          } 
    });
    
    function updateLabel(label,element){
      var anchor = $("<a></a>");
      
      anchor.append(label);
      anchor.attr('href','/?uri='+$(element).text());
      
      $(element).html(anchor);
      
    }
  
});