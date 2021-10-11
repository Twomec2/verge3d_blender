<%inherit file="dialog.tpl"/>

<%block name="blkDialogId">diaDelete</%block>

<%block name="blkDialogHeader">
  App Removed
</%block>

<%block name="blkDialogContent">
  <div class="dialog-icon dialog-icon-delete"></div>
  <div class="dialog-right-content-short">
    <div class="dialog-text-center">
      Application “${title}” <br> has been moved to Trash.
    </div>
    <button id="diaDeleteOk" class="button">Fine!</button>
  </div>
</%block>

<%block name="blkDialogScript">
  function diaDeleteCloseHandler() {
      destroyDialog("diaDelete");
      // always redirect to main page
      window.location.href = '/';
  }

  diaDeleteClose.addEventListener('click', diaDeleteCloseHandler);
  diaDeleteOk.addEventListener('click', diaDeleteCloseHandler);

  focusElem('diaDeleteOk');
</%block>
