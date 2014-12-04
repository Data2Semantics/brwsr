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

              if ($(element).attr('lang') != '') {
                var lang = $("<span></span>");
                lang.text($(element).attr('lang'));
                span.append(lang);
              }
              
              span.append(element_text.substr(0,200) + '...');
              
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
      anchor.attr('href',$(element).attr('local'));
      
     
      
      var icon = $("<span class='glyphicon glyphicon-link' aria-hidden='true'></span>");
      var icon_anchor = $('<a></a>');
      icon_anchor.append(icon)
      icon_anchor.attr('href',$(element).text());
      icon_anchor.css('margin-right','3px');
      
      var span = $("<span></span>");
      

      
      
      span.append(icon_anchor);
      span.append(anchor);
      
       $(element).html(span);
      
    }
  
});