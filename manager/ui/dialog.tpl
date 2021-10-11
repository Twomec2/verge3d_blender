<div class="dialog-bg" id="<%block name="blkDialogId"/>">
  <div class="dialog">
    <div class="dialog-header">
      <div class="dialog-header-text">
        <%block name="blkDialogHeader"/>
      </div>
      <div class="dialog-header-close" id="${self.blkDialogId()}Close"></div>
    </div>
    <div class="dialog-content" id="${self.blkDialogId()}Content">
      <%block name="blkDialogContent"/>
    </div>
  </div>
  <script>
    <%block name="blkDialogScript">
      document.getElementById('${self.blkDialogId()}Close').addEventListener('click', function() {
          closeDialog('${self.blkDialogId()}');
      });
    </%block>
  </script>
</div>

