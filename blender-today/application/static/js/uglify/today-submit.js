$(document).ready(function() {
        var csrftoken = $('meta[name=csrf-token]').attr('content');

        $.ajaxSetup({
          beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
              xhr.setRequestHeader("X-CSRFToken", csrftoken)
            }
          }
        });

        $("#submit_post_form").on("submit", function (e) {
            e.preventDefault();
            $('.post-submit-field-submit').html('<i class="fa fa-spinner fa-spin"></i> <i>Submitting...</i>');
            var data = $(this).serialize();
            url = $(this).attr('action');
            var formData = new FormData($(this)[0]);
            $.ajax({
                  url: url,
                  type: 'POST',
                  data: formData,
                  processData: false,
                  contentType: false,
                  cache: false
                })
            .done(function(data){
                $('.post-submit-field-submit').css('background-color', '#5cb85c');
                $('.post-submit-field-submit').html('<i class="fa fa-check"></i> Success!');
                window.location.replace(data['post_url']);
            })
            .fail(function(data){
              $('.post-submit-field-submit').html('<i class="fa fa-frown-o fa-spin"></i> Houston!');
            });
        });

        (function() {
          var dlgtrigger = document.querySelector( '[data-dialog]' ),
            somedialog = document.getElementById( dlgtrigger.getAttribute( 'data-dialog' ) ),
            dlg = new DialogFx( somedialog );
          dlgtrigger.addEventListener( 'click', dlg.toggle.bind(dlg) );
        })();

        CKEDITOR.replace( 'post_content', {
          removePlugins: 'elementspath',
          resize_enabled: false
        });
        CKEDITOR.config.forcePasteAsPlainText = true;
        CKEDITOR.instances['post_content'].on('change', function() { CKEDITOR.instances['post_content'].updateElement() });

        $('.select-change').click(function(){
          $('#post_type_id').val($(this).data('val'));
          $('.select-change').each(function() {
            $(this).removeClass('activato');
          });

          $(this).addClass('activato');

          $('.post-submit-div-title').show();
          $('.post-submit-div-category').show();
          $('.post-submit-div-picture').show();
          $('.post-submit-div-submit').show();

          if ($('#post_type_id').val() == 1){
            $('.post-submit-link').show();
            $('.post-submit-article').hide();
          };
          if ($('#post_type_id').val() == 2){
            $('.post-submit-link').hide();
            $('.post-submit-article').show();
          };
        });
      $('.post-index-item-type').click(function(e){
        $(this).parent().parent().find('.post-index-item-type-ripple').css('display', 'block');
      });
      $('.post-index-item-title').click(function(e){
        $(this).parent().find('.post-index-item-type-ripple').css('display', 'block');
      });
});
