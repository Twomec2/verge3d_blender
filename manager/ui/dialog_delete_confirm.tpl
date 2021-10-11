<%inherit file="dialog.tpl"/>

<%block name="blkDialogId">diaDeleteConfirm</%block>

<%block name="blkDialogHeader">
  Move to Trash?
</%block>

<%block name="blkDialogContent">
  <div class="dialog-icon dialog-icon-delete"></div>
  <div class="dialog-right-content-short">
    <div class="dialog-text dialog-text-delete">
    Are you sure you want to move<br><a href="${manageURL}" class="colored-link">${title}</a> to Trash?</div>
    <div class="two-buttons">
      <div><button class="button delete-button" id="deleteYes">Yes</button></div>
      <div><button class="button" id="deleteNo">No</button></div>
    </div>
  </div>
</%block>

<%block name="blkDialogScript">
  diaDeleteConfirmClose.addEventListener('click', function() {
      destroyDialog('diaDeleteConfirm');
  });

  deleteYes.addEventListener('click', function() {
      makeRequest('/delete/?app=${app | u}', null, function(response) {
          var dia = appendDialog(response);
          openDialog(dia);
      });

      destroyDialog('diaDeleteConfirm');
  });

  deleteNo.addEventListener('click', function() {
      destroyDialog('diaDeleteConfirm');
  });

  focusElem('deleteNo');

</%block>
