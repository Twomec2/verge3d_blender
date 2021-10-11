
<html>
<head>
  <title>Verge3D App Manager</title>
  <%include file="head.tpl"/>
</head>

<body>
  <div class="main-panel">

    <%include file="banner.tpl"/>

    <%
        import os.path

        leftItems = []
        rightItems = []

        prevItemDirName = None

        for itemType in ['html', 'gltf']:
            for item in app[itemType]:
                item['type'] = itemType

                dirName = os.path.dirname(item['path'])

                if prevItemDirName != dirName:
                    item['dirCut'] = True
                else:
                    item['dirCut'] = False

                prevItemDirName = dirName

                leftItems.append(item)

        prevItemDirName = None

        for itemType in ['blend', 'max', 'maya']:
            for item in app[itemType]:
                item['type'] = itemType

                dirName = os.path.dirname(item['path'])

                if prevItemDirName != dirName:
                    item['dirCut'] = True
                else:
                    item['dirCut'] = False

                prevItemDirName = dirName

                rightItems.append(item)

        # put main first then sort by path string
        rightItems.sort(key=lambda elem: 'a' + elem['path'] if elem['isMain'] else 'b' + elem['path'])

        rowsDiff = len(leftItems) - len(rightItems)
          
        if rowsDiff < 0:
            for _ in range(abs(rowsDiff)):
                leftItems.append({'type': 'empty'})
        elif rowsDiff > 0:
            for _ in range(rowsDiff):
                rightItems.append({'type': 'empty'})

    %>

    <table class="app-assets-list">
      <thead>
        <tr>
          <th colspan=2>runnables</th>
          <th colspan=2>scenes</th>
        </tr>
      </thead>
      <tbody>
        % for i, left, right in zip(range(len(leftItems)), leftItems, rightItems):
          <tr class="filterable">
            % if left['type'] == 'html':
              <td class="${'dir-cut' if left['dirCut'] else ''}">
                % if i == 0:
                  <a href="${left['url']}" target="_blank" class="app-icon app-icon-html-main" title="Run app: ${left['path']}"></a>
                % else:
                  <a href="${left['url']}" target="_blank" class="app-icon app-icon-html" title="Run HTML: ${left['path']}"></a>
                % endif
              </td>
              <td class="${'dir-cut' if left['dirCut'] else ''}">
                % if i == 0:
                  <a href="${left['url']}" target="_blank" class="asset-title" title="Run app: ${left['path']}">${left['name']}</a>
                % else:
                  <a href="${left['url']}" target="_blank" class="asset-title" title="Run HTML: ${left['path']}">${left['name']}</a>
                % endif
              </td>

            % elif left['type'] == 'gltf':
              <td class="${'dir-cut' if left['dirCut'] else ''}">
                <a href="${left['url']}" target="_blank" class="app-icon app-icon-gltf" title="View scene: ${left['path']}"></a>
              </td>
              <td class="${'dir-cut' if left['dirCut'] else ''}">
                <a href="${left['url']}" target="_blank" class="asset-title" title="View scene: ${left['path']}">${left['name']}</a>
              </td>

            % elif left['type'] == 'empty':
              <td></td><td></td>
            % endif

            % if right['type'] == 'blend':
              <td class="${'dir-cut' if right['dirCut'] else ''}">
                <a href="javascript:void(0);" onclick=openFile("${right['url']}") class="app-icon app-icon-blend${'-main' if right['isMain'] else ''}" title="Open Blender file: ${right['path']}"></a>
              </td>
              <td class="${'dir-cut' if right['dirCut'] else ''}">
                <a class="asset-title" href="javascript:void(0);" onclick=openFile("${right['url']}") title="Open Blender file: ${right['path']}">${right['name']}</a>
              </td>

            % elif right['type'] == 'max':
              <td class="${'dir-cut' if right['dirCut'] else ''}">
                <a href="javascript:void(0);" onclick=openFile("${right['url']}") class="app-icon app-icon-max${'-main' if right['isMain'] else ''}" title="Open 3ds Max file: ${right['path']}"></a>
              </td>
              <td class="${'dir-cut' if right['dirCut'] else ''}">
                <a class="asset-title" href="javascript:void(0);" onclick=openFile("${right['url']}") title="Open 3ds Max file: ${right['path']}">${right['name']}</a>
              </td>

            % elif right['type'] == 'maya':
              <td class="${'dir-cut' if right['dirCut'] else ''}">
                <a href="javascript:void(0);" onclick=openFile("${right['url']}") class="app-icon app-icon-maya${'-main' if right['isMain'] else ''}" title="Open Maya file: ${right['path']}"></a>
              </td>
              <td class="${'dir-cut' if right['dirCut'] else ''}">
                <a class="asset-title" href="javascript:void(0);" onclick=openFile("${right['url']}") title="Open Maya file: ${right['path']}">${right['name']}</a>
              </td>

            % elif left['type'] == 'empty':
              <td></td><td></td>
            % endif
          </tr>
        % endfor
      </tbody>
      <tfoot><tr><td colspan=4>© Soft8Soft LLC</td></tr></tfoot>
    </table>
  
  </div>

  <%include file="toolbar.tpl"/>
  <%include file="toolbar_app.tpl"/>
  <%include file="dialog_publishing.tpl"/>
  <%include file="dialog_qr_code.tpl"/>

</body>
</html>
