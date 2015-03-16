/**
 * @AutoLink plugin for CKEditor (2013.08.23)
 * @description Generate a hyperlink automatically when you typing a URL-like string(Auto-add <a> label to non-IE browsers)
 * @author gnodiah(Hayden Wei)
 * @version 1.1
 * @updated 2015-01-20
 */
CKEDITOR.plugins.add('autolink', {
  init: function(editor) {
    editor.on('instanceReady', function() {
      var cont = 0;

      // skip IE
      // especially IE 11, because its User-Agent is Gecko, not MSIE
      if (CKEDITOR.env.ie || (CKEDITOR.env.gecko && CKEDITOR.env.version === 110000)) return;

      var fillChar = CKEDITOR.env.ie && CKEDITOR.env.version == '6' ? '\ufeff' : '\u200B';
      var isFillChar = function (node, isInStart) {
        return node.nodeType == 3 && !node.nodeValue.replace(new RegExp((isInStart ? '^' : '' ) + fillChar), '').length
      }
      var isBody = function (node) {
        return  node && node.nodeType == 1 && node.tagName.toLowerCase() == 'body';
      }
      var html = function (str) {
        return str ? str.replace(/&((g|l|quo)t|amp|#39);/g, function (m) {
          return {
            '&lt;':'<',
            '&amp;':'&',
            '&quot;':'"',
            '&gt;':'>',
            '&#39;':"'"
          }[m]
        }) : '';
      }
      var isArray = function (obj) {
        return Object.prototype.toString.apply(obj) == '[object Array]';
      }
      var isBody = function (node) {
        return  node && node.nodeType == 1 && node.tagName.toLowerCase() == 'body';
      }
      var listToMap = function (list) {
        if (!list) return {};
        list = isArray(list) ? list : list.split(',');
        for (var i = 0, ci, obj = {}; ci = list[i++];) {
          obj[ci.toUpperCase()] = obj[ci] = 1;
        }
        return obj;
      }
      var findParent = function (node, filterFn, includeSelf) {
        if (node && !isBody(node)) {
          node = includeSelf ? node : node.parentNode;
          while (node) {
            if (!filterFn || filterFn(node) || isBody(node)) {
              return filterFn && !filterFn(node) && isBody(node) ? null : node;
            }
            node = node.parentNode;
          }
        }
        return null;
      }
      var findParentByTagName = function (node, tagNames, includeSelf, excludeFn) {
        tagNames = listToMap(isArray(tagNames) ? tagNames : [tagNames]);
        return findParent(node, function (node) {
          return tagNames[node.tagName] && !(excludeFn && excludeFn(node));
         }, includeSelf);
      }

      editor.document.on('reset', function() {
        cont = 0;
      });
      editor.autolink = function(e){
        var sel = editor.getSelection().getNative(),
            range = sel.getRangeAt(0).cloneRange(),
            offset,
            charCode;

        var start = range.startContainer;
        while (start.nodeType == 1 && range.startOffset > 0) {
          start = range.startContainer.childNodes[range.startOffset - 1];
          if (!start) break;

          range.setStart(start, start.nodeType == 1 ? start.childNodes.length : start.nodeValue.length);
          range.collapse(true);
          start = range.startContainer;
        }

        do {
          if (range.startOffset == 0) {
            start = range.startContainer.previousSibling;

            while (start && start.nodeType == 1) {
              if (CKEDITOR.env.gecko && start.firstChild)
                start = start.firstChild;
              else
                start = start.lastChild;
            }
            if (!start || isFillChar(start)) break;
            offset = start.nodeValue.length;
          } else {
            start = range.startContainer;
            offset = range.startOffset;
          }
          range.setStart(start, offset - 1);
          charCode = range.toString().charCodeAt(0);
        } while (charCode != 160 && charCode != 32);

        if (range.toString().replace(new RegExp(fillChar, 'g'), '').match(/(?:https?:\/\/|ssh:\/\/|ftp:\/\/|file:\/|www\.)/i)) {
          while(range.toString().length){
            if(/^(?:https?:\/\/|ssh:\/\/|ftp:\/\/|file:\/|www\.)/i.test(range.toString())) break;

            try{
              range.setStart(range.startContainer,range.startOffset+1);
            } catch(e) {
              var start = range.startContainer;
              while (!(next = start.nextSibling)) {
                if (isBody(start)) return;
                start = start.parentNode;
              }
              range.setStart(next,0);
            }
          }

          if (findParentByTagName(range.startContainer,'a',true)) return;

          var a = document.createElement('a'), text = document.createTextNode(' '), href;

          editor.undoManger && editor.undoManger.save();
          a.appendChild(range.extractContents());
          a.href = a.innerHTML = a.innerHTML.replace(/<[^>]+>/g, '');
          href = a.getAttribute("href").replace(new RegExp(fillChar,'g'), '');
          href = /^(?:https?:\/\/)/ig.test(href) ? href : "http://"+ href;
          a.setAttribute('_src', html(href));
          a.href = html(href);

          range.insertNode(a);
          a.parentNode.insertBefore(text, a.nextSibling);
          range.setStart(text.nextSibling, 0);
          range.collapse(true);
          sel.removeAllRanges();
          sel.addRange(range);
          editor.undoManger && editor.undoManger.save();
        }
      }

      // bind key event
      if (CKEDITOR.env.webkit) {
        editor.on("key", function(e) {
          if (e.data.keyCode === 32 || e.data.keyCode === 13) editor.autolink(e);
        });
      } else { // mainly for Firefox
        editor.document.on("keypress", function(e) {
          if (e.data.getKey() === 32 || e.data.getKey() === 13) editor.autolink(e);
        });
      }
    });
  }
});
