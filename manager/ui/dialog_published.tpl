<%inherit file="dialog.tpl"/>

<%block name="blkDialogId">diaPublished</%block>

<%block name="blkDialogHeader">
  Uploading Finished!
</%block>

<%block name="blkDialogContent">

  <div class="published-cont">

    <div class="dialog-text-center">You did it!</div>

    <div class="dialog-text">Your web application has been successfully uploaded to Verge3D Network. It is time to share it via social media, a direct link or embedded into your website.</div>

    % for upload in uploadsViewInfo:

      <div class="published-item-frame">

        <div class="published-item-header">

          <a href="${upload['url']}" target="_blank"><span class="app-icon app-icon-html-main published-app-icon"></span>${upload['shorturl']}</a>

          <div class="published-socials">
            <a href="http://twitter.com/share?url=${upload['url']}&text=${upload['socialText']}&hashtags=verge3d,3dweb" target="_blank" title="Share ${upload['title']} on Twitter" class="share-icon share-icon-twitter"></a>

            <a href="http://www.facebook.com/sharer/sharer.php?u=${upload['url']}" target="_blank" title="Share ${upload['title']} on Facebook" class="share-icon share-icon-facebook">
            </a>

            <a href="http://reddit.com/submit?url=${upload['url']}&title=${upload['socialText']}" target="_blank" title="Share ${upload['title']} on Reddit" class="share-icon share-icon-reddit">
            </a>

            <a href="http://www.linkedin.com/shareArticle?url=${upload['url']}&title=${upload['socialText']}&summary=${upload['socialText']}" target="_blank" title="Share ${upload['title']} on LinkedIn" class="share-icon share-icon-linkedin"></a>

            <a href="https://vk.com/share.php?url=${upload['url']}" target="_blank" title="Share ${upload['title']} on VK" class="share-icon share-icon-vk"></a>

            <a href="http://service.weibo.com/share/share.php?url=${upload['url']}&title=${upload['socialText']}" target="_blank" title="Share ${upload['title']} on Weibo" class="share-icon share-icon-weibo"></a>

            <a href="${upload['url']}" title="${upload['title']} - QR Code" class="share-icon share-icon-qrcode"></a>
          </div>
        </div>

        <div class="published-item-snippets">
          <div class="dialog-text">Direct Link <a href="javascript:void(0);" onclick=copyTextArea("publishedHTMLSnippet") class="clipboard-copy"></a></div>

          <textarea class="published-snippet" id="publishedHTMLSnippet" title="Direct link to the application HTML file">${upload['url']}</textarea>

          <div class="dialog-text">Embed <a href="javascript:void(0);" onclick=copyTextArea("publishedIFrameSnippet") class="clipboard-copy"></a></div>

          <textarea class="published-snippet" id="publishedIFrameSnippet" title="HTML code for embedding">&lt;iframe width=&#34;1024&#34; height=&#34;640&#34; allowfullscreen src=&#34;${upload['url']}&#34;&gt;&lt;/iframe&gt;&#10;</textarea>
        </div>
        
      </div>

    %endfor

    <div class="dialog-text-center"><span>You can find the full list of uploaded files in the</span><a href="/storage/net/?req=status" class="network-directory-icon"></a></div>

    % if licenseInfo['type'] == 'TRIAL':
        <hr>
        <div class="dialog-text-center published-trialwarning">Please note that for this trial version we promise to keep your data for 30 days only. Afterwards, uploaded files may get deleted!</div>
    % endif

  </div>

</%block>

<%block name="blkDialogScript">

  diaPublishedClose.addEventListener('click', function() {
      destroyDialog('diaPublished');
  });

  function processQRCode(qrCodeElem) {
      var dataURL = createQRCode(qrCodeElem.href);
      qrCodeElem.href = dataURL;

      qrCodeElem.addEventListener('click', function(event) {
          // do not destroy here
          closeDialog('diaPublished');

          openDialog('diaQRCode');

          diaQRCode.querySelector('.dialog-header-text').innerText = qrCodeElem.title;
          qrCodeImage.src = dataURL;

          event.preventDefault();
      });
  }

  var qrs = document.getElementsByClassName('share-icon share-icon-qrcode');

  for (var i = 0; i < qrs.length; i++) {
      var qr = qrs[i];
      processQRCode(qr);
  };

</%block>
