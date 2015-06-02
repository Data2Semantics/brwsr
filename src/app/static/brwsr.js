$( document ).ready(function() {
 
    $(".resource").each(function(index){
      var element = this;
      var element_text = $(this).text();
      
      if (element_text && element_text.substr(0,4) == 'http') {
            updateLabel(element_text,element);
            $.get('http://preflabel.org/api/v1/label/'+encodeURIComponent($(element).text())+"?callback=?", function(data){
              updateLabel(data,element);
            });
      } 
    });
    
    $(".literal").each(function(index){
        var element = this;
        var element_text = $(this).text();
        if (element_text.length > 200 ) {

              var span = $('<span></span>');

              if ($(element).attr('lang') != '') {
                var lang = $("<span></span>");
                lang.text($(element).attr('lang'));
                span.append(lang);
              }
              
              var dotdot = $('<span>...</span>');
              var head = $('<span></span>');
              head.append(element_text.substr(0,200));
              
              var open = $('<span class="glyphicon glyphicon-chevron-right" aria-hidden="true"></span>');
              
              var tail = $('<span></span>');
              tail.append(element_text.substr(200));
              
              var close = $('<span class="glyphicon glyphicon-chevron-left" aria-hidden="true"></span>');
              
              span.append(head);
              span.append(dotdot);
              span.append(open);
              span.append(tail);
              span.append(close);
              tail.hide();
              close.hide();
              
              span.on('click', function(e){
                close.toggle();
                tail.toggle();
                dotdot.toggle();
                open.toggle();
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