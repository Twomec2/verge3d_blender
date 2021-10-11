<%inherit file="dialog.tpl"/>

<%block name="blkDialogId">diaCreateNativeAppDone</%block>

<%block name="blkDialogHeader">
  Downloading App Template...
</%block>

<%block name="blkDialogContent">
  <div class="dialog-text-center">
    Your app template is ready. If the download doesn't start immediately, click <a href="${downloadURL}" download id="downloadNativeAppTemplate" class="colored-link">here</a>.
  </div>

  <div class="dialog-text-center">
    Follow next steps as described in the User Manual: <a href="https://www.soft8soft.com/docs/manual/en/introduction/Creating-Desktop-Apps.html" target="_blank" class="colored-link">desktop</a>, <a href="https://www.soft8soft.com/docs/manual/en/introduction/Creating-Mobile-Apps.html" target="_blank" class="colored-link">mobile</a>.
  </div>

  <button id="diaCreateNativeAppDoneOk" class="button">Got It!</button>
</%block>

<%block name="blkDialogScript">
  function diaCreateNativeAppDoneCloseHandler() {
      destroyDialog('diaCreateNativeAppDone');
  }

  diaCreateNativeAppDoneClose.addEventListener('click', diaCreateNativeAppDoneCloseHandler);
  diaCreateNativeAppDoneOk.addEventListener('click', diaCreateNativeAppDoneCloseHandler);

  focusElem('diaCreateNativeAppDoneOk');
  document.getElementById('downloadNativeAppTemplate').click();
</%block>
