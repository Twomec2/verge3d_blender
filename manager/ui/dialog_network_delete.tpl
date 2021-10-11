<%inherit file="dialog.tpl"/>

<%block name="blkDialogId">diaNetworkDelete</%block>

<%block name="blkDialogHeader">
  Delete Status
</%block>

<%block name="blkDialogContent">
  <div class="dialog-text">
    Delete operation complete, ${numFiles} file(s) removed.
  </div>
</%block>

<%block name="blkDialogScript">
  diaNetworkDeleteClose.addEventListener('click', function() {
      destroyDialog("diaNetworkDelete");
      document.location.reload(true);
  });
</%block>
