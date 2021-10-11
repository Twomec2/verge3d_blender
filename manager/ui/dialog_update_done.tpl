<%inherit file="dialog.tpl"/>

<%block name="blkDialogId">diaUpdateDone</%block>

<%block name="blkDialogHeader">
  App Updated
</%block>

<%block name="blkDialogContent">
  <div class="dialog-text-center">
    The ${title} app has been successfully updated.
  </div>
  <button id="diaUpdateDoneOk" class="button">Ok</button>
</%block>

<%block name="blkDialogScript">
  diaUpdateDoneClose.addEventListener('click', function() {
      destroyDialog('diaUpdateDone');
  });
  diaUpdateDoneOk.addEventListener('click', function() {
      destroyDialog('diaUpdateDone');
  });

  focusElem('diaUpdateDoneOk');

  if (appManager.updatedAppIconElem) {

      var icon = appManager.updatedAppIconElem;

      if (icon.classList.contains('app-icon')) {
          icon.classList.remove('app-icon-update');
          icon.classList.add('app-icon-update-inactive');
      } else {
          icon.classList.add('hidden');
      }
  }
</%block>
