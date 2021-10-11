<html>
<head>
  <title>Verge3D App Manager</title>
  <%include file="head.tpl"/>
  <script src="/manager/js/network.js"></script>
</head>

<%!
    MAX_VISIBLE_ICONS = 5
    iconCounter = 0

    def cut():
        global iconCounter
        iconCounter += 1
        if iconCounter == (MAX_VISIBLE_ICONS + 1):
            return '<div class="app-icon-cut hidden">'
        else:
            return ''

    def cutEnd():
        global iconCounter
        if iconCounter > MAX_VISIBLE_ICONS:
            iconCounter = 0
            return '</div>'
        else:
            iconCounter = 0
            return ''

    def appIsCollapsible(app):
        if len(app['html']) + len(app['gltf']) > MAX_VISIBLE_ICONS:
            return True
        elif len(app['blend']) + len(app['max']) > MAX_VISIBLE_ICONS:
            return True
        else:
            return False
%>


<body>
  <div class="main-panel">

    <%include file="banner.tpl"/>

    <table class="app-list">
      <thead>
        <tr>
          <th colspan=2>app name</th>
          <th>runnables</th>
          <th>scenes</th>
          <th>operations</th>
        </tr>
      </thead>
      <tbody>
        % for app in apps:
          <tr class="filterable">
            <td>
              <a href="javascript:void(0);" onclick="toggleCollapsible(this)" class="${'app-collapsed' if appIsCollapsible(app) else 'app-non-collapsible'}" title="Expand / Collapse App"></a>
            </td>
            <td>
              <span class="app-title" title="${app['name']}"><span class="app-number">${loop.index+1}</span><a href="${app['manageURL']}">${app['title']}</a></span>
            </td>

            <td>
              % for html in app['html']:
                ${cut()}
                % if loop.index == 0:
                  <a href="${html['url']}" target="_blank" class="app-icon app-icon-html-main" title="Run app: ${html['path']}"></a>
                % else:
                  <a href="${html['url']}" target="_blank" class="app-icon app-icon-html" title="Run HTML: ${html['path']}"></a>
                % endif
              % endfor

              % for gltf in app['gltf']:
                ${cut()}
                  <a href="${gltf['url']}" target="_blank" class="app-icon app-icon-gltf" title="View scene: ${gltf['path']}"></a>
              % endfor
              ${cutEnd()}
            </td>

            <td>
              % for blend in app['blend']:
                ${cut()}
                <a href="javascript:void(0);" onclick=openFile("${blend['url']}") 
                    class="app-icon app-icon-blend${'-main' if blend['isMain'] else ''}"
                    title="Open Blender file: ${blend['path']}"></a>
              % endfor

              % for maxx in app['max']:
                ${cut()}
                <a href="javascript:void(0);" onclick=openFile("${maxx['url']}")
                    class="app-icon app-icon-max${'-main' if maxx['isMain'] else ''}"
                    title="Open 3ds Max file: ${maxx['path']}"></a>
              % endfor

              % for maya in app['maya']:
                ${cut()}
                <a href="javascript:void(0);" onclick=openFile("${maya['url']}")
                    class="app-icon app-icon-maya${'-main' if maya['isMain'] else ''}"
                    title="Open Maya file: ${maya['path']}"></a>
              % endfor
              ${cutEnd()}
            </td>

            <td>
              % if app['puzzles']:
                % if app['puzzles']['logicExists']:
                  <a href="${app['puzzles']['url']}" target="_blank" class="app-icon app-icon-puzzles-edit" title="Edit Puzzles"></a>
                % else:
                  <a href="${app['puzzles']['url']}" target="_blank" class="app-icon app-icon-puzzles-new" title="Create Puzzles"></a>
                % endif
              % endif

              <a href="javascript:void(0);" onclick=openFile("${app['url']}") class="app-icon app-icon-open-folder" title="Open app folder"></a>

              <a href="javascript:void(0);" onclick=publishApp("${app['name'] | u}",false) class="app-icon app-icon-publish-dir" title="Publish on the Web using Verge3D Network"></a>

              % if app['needsUpdate']:
                <a href="javascript:void(0);" onclick=updateApp("${app['name'] | u}",this) class="app-icon app-icon-update" title="Update application"></a>
              % else:
                <a href="javascript:void(0);" class="app-icon app-icon-update-inactive" title="This application is already updated"></a>
              % endif

              <a href="javascript:void(0);" onclick=deleteApp("${app['name'] | u}") class="app-icon app-icon-delete" title="Delete app folder"></a>

            </td>
          </tr>
        % endfor
      </tbody>
      <tfoot><tr><td colspan=5>© Soft8Soft LLC</td></tr></tfoot>
    </table>

  </div>

  <%include file="toolbar.tpl"/>
  <%include file="dialog_publishing.tpl"/>
  <%include file="dialog_qr_code.tpl"/>

</body>
</html>
