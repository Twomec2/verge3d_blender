#!/usr/bin/env python3

import os, sys

join = os.path.join
norm = os.path.normpath

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, join(BASE_DIR, 'lib'))

import base64, datetime, filecmp, hashlib, json, mimetypes, pathlib, re, shutil, ssl, string, subprocess, tempfile, zipfile

import urllib.parse, urllib.request

import plistlib

import asyncio
import concurrent.futures

import tornado.ioloop
import tornado.web
import tornado.httpclient

import ziptools

from mako.lookup import TemplateLookup, Template
import boto3, botocore.client

from xml.dom import minidom

import send2trash

from profilehooks import profile

PORT = 8668
APPS = 'applications'

KEY_LEN = 54
HASH_SIZE = 0xFFFF

SETTINGS_JSON = 'settings.json'
STOCK_APPS_JSON = 'stock_apps.json'
APP_TEMPLATE_JSON = 'template.json'

LOGIC_JS = 'visual_logic.js'
LOGIC_XML = 'visual_logic.xml'
PUZZLES_DIR = 'puzzles'
PLUGINS_DIR = 'plugins'
LIBRARY_XML = 'my_library.xml'
BACKUP_LIBRARY_DIR = 'library_backup'
PUZZLE_PLUGIN_INIT_FILE_NAME = 'init.plug'
PUZZLE_PLUGIN_BLOCK_FILE_EXT = 'block'

APP_DATA_DIR = 'v3d_app_data'
BACKUP_PUZZLES_DIR = 'puzzles_backup'
BACKUP_UPDATE_DIR = 'update_backup'

CDN_HOST = 'https://cdn.soft8soft.com/'
ELECTRON_RELEASE = 'https://api.github.com/repos/electron/electron/releases/41745641'

CDN_IGNORE = [
    APP_DATA_DIR + '/*',
    APP_DATA_DIR + '/*/*', # including subfolders
    'visual_logic.xml',
    '.blend1',
    '.blend2',
    '*.blend',
    '*.max',
    '*.ma',
    '*.mb'
]

SERVER_MAX_BODY_SIZE = 2*1024*1024*1024 # 2GB

AUTH_ADDRESS = 'auth.soft8soft.com'
AUTH_PORT = 443

ALLOWED_NET_REQUESTS = ['status', 'upload', 'delete', 'progress', 'cancel']

ACCESS_DENIED_MSG = '<span class="red">Access is denied. Make sure that you have permissions to write into Verge3D installation directory.</span>'

class NothingToUploadException(Exception):
    pass

class UploadCancelledException(Exception):
    pass


class AppManagerServer(object):

    def __init__(self):
        self.needRestart = False
        self.asyncioLoop = None

        # NOTE: add missing WebAssembly mime type
        # works for both Tornado and S3/CloudFront
        mimetypes.add_type('application/wasm', '.wasm')
        mimetypes.add_type('model/vnd.usdz+zip', '.usdz')

    def copyTreeMerge(self, topSrcDir, topDstDir):

        # NOTE: for pathlib paths
        topSrcDir = str(topSrcDir)
        topDstDir = str(topDstDir)

        for srcDir, dirs, files in os.walk(topSrcDir):

            dstDir = srcDir.replace(topSrcDir, topDstDir, 1)

            if not os.path.exists(dstDir):
                os.makedirs(dstDir)

            for file_ in files:
                srcFile = os.path.join(srcDir, file_)
                dstFile = os.path.join(dstDir, file_)

                if os.path.exists(dstFile):
                    os.remove(dstFile)

                shutil.copy2(srcFile, dstDir)

    def getLocalIP(self):
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except:
            IP = ''
        finally:
            s.close()

        return IP

    def runPython(self, args):
        pythonPath = sys.executable

        # NOTE: sys.executable may point to modelling suite executable

        # COMPAT: for Blender <3.0 binary_path_python used instead of incorrect sys.executable
        try:
            import bpy
            pythonPath = bpy.app.binary_path_python
        except ImportError:
            pass
        except AttributeError:
            pass

        # detect Maya
        try:
            import maya.cmds
            pythonPath = join(os.getenv('MAYA_LOCATION'), 'bin', 'mayapy')
        except ImportError:
            pass

        if os.name == 'nt':
            # disable popup console window
            si = subprocess.STARTUPINFO()
            si.dwFlags = subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            retStr = subprocess.check_output([pythonPath] + args, startupinfo=si)
        else:
            retStr = subprocess.check_output([pythonPath] + args)

        return retStr

    def loadSettings(self):
        self.amSettings = {}

        try:
            with open(join(BASE_DIR, SETTINGS_JSON), 'r', encoding='utf-8') as f:
                self.amSettings = json.load(f)
        except OSError:
            # using default server settings
            pass
        except json.decoder.JSONDecodeError:
            print('Settings decoding error')

        self.amSettings.setdefault('checkForUpdates', True)
        self.amSettings.setdefault('theme', 'light')
        self.amSettings.setdefault('hideStockApps', False)
        self.amSettings.setdefault('uploadSources', False)
        self.amSettings.setdefault('externalInterface', False)
        self.amSettings.setdefault('cacheMaxAge', 15) # minutes
        self.amSettings.setdefault('extAppsDirectory', '')
        self.amSettings.setdefault('appTemplates', [
            {
                "name": "Standard Light",
                "description": "Create a generic Puzzles-enabled app suitable for most users (light theme)"
            },
            {
                "name": "Standard Dark",
                "description": "Create a generic Puzzles-enabled app suitable for most users (dark theme)"
            },
            {
                "name": "Blank Scene",
                "description": "Create a blank Puzzles-enabled app"
            },
            {
                "name": "Code-Based",
                "description": "Create a starter set of HTML/CSS/JavaScript files for use by web developers"
            }
        ])

        self.amSettings.setdefault('licenseKey', '')
        self.amSettings.setdefault('licenseKeyVersion', '')

        if 'externalAddress' in self.amSettings:
            del self.amSettings['externalAddress']

        if self.amSettings['externalInterface']:
            ip = self.getLocalIP()
            if ip:
                self.amSettings['externalAddress'] = 'http://{0}:{1}/'.format(ip, PORT);

        if self.amSettings['hideStockApps']:
            with open(join(BASE_DIR, STOCK_APPS_JSON), 'r', encoding='utf-8') as f:
                self.amSettings['stockApps'] = json.load(f)

        # COMPAT: <3.7
        # TODO: remove ASAP, since it may introduce bugs when users clean up their templates
        appTemplates = self.amSettings['appTemplates']
        noBlank = True
        for template in appTemplates:
            if template['name'] == 'Blank Scene':
                noBlank = False
                break
        if noBlank:
            print('Adding missing Blank Scene template')
            appTemplates.insert(2, {
                "name": "Blank Scene",
                "description": "Create a blank Puzzles-enabled app"
            })

    def saveSettings(self):
        with open(join(BASE_DIR, SETTINGS_JSON), 'w', encoding='utf-8') as f:
            json.dump(self.amSettings, f, sort_keys=True, indent=4, separators=(', ', ': '), ensure_ascii=False)
            print('App manager settings saved')

    def handleUpdate(self):
        licenseInfo = self.getLicenseInfo()

        if licenseInfo['maintenance'] and licenseInfo['releaseVersion'] != self.amSettings['licenseKeyVersion']:

            print('Updating licensing information')

            rootDir = self.getRootDir()

            for d in [APPS, 'build']:
                for v3dpath in pathlib.Path(join(rootDir, d)).rglob('v3d*.js'):
                    path = str(v3dpath)
                    self.replaceEngineKey(path, self.amSettings['licenseKey'])

            self.amSettings['licenseKeyVersion'] = licenseInfo['releaseVersion']
            self.saveSettings()

    def pathToUrl(self, path, quote=True, replaceBackslash=True, makeAbs=False):
        path = str(path)

        if replaceBackslash:
            path = path.replace('\\', '/')
        if quote:
            path = urllib.parse.quote(path, safe='/:')
        if makeAbs and path[0] != '/':
            path = '/' + path
        return path

    def replaceAmp(self, url):
        return url.replace('&', '&amp;')

    def urlBasename(self, url):
        path = urllib.parse.urlparse(url).path
        return os.path.basename(path)

    def argBool(self, argument):
        if argument.lower() in ['1', 'yes', 'y']:
            return True
        else:
            return False

    def getRootDir(self, usePath=False):
        if usePath:
            return (pathlib.Path(BASE_DIR) / '..').resolve()
        else:
            return norm(join(BASE_DIR, '..'))

    def resolveURLPath(self, path):
        """Convert URL path to file system path"""

        extAppsDir = self.getExtAppsDir()
        if extAppsDir and path.startswith('/ext/'):
            return (extAppsDir / path.replace('/ext/' + extAppsDir.name + '/', '')).resolve()
        else:
            return self.getRootDir(True) / path.lstrip('/')

    async def runAsync(self, func, *args, **kwargs):
        """Convert sync function to awaitable async function and run it"""
        executor = concurrent.futures.ThreadPoolExecutor(1)
        return await asyncio.wrap_future(executor.submit(func, *args, **kwargs))

    def genUpdateInfo(self, appDir, hcjFiles):
        """appDir is absolute, html/css/js files are app relative"""

        MODULES = ['v3d.js', 'v3d.legacy.js', 'opentype.js', 'webxr-polyfill.js', 'ammo.js', 'ammo.wasm.js', 'ammo.wasm.wasm']

        modules = []

        needUpdate = False

        for m in MODULES:
            m_src = pathlib.Path(BASE_DIR) / '..' / 'build' / m
            m_dst = appDir / m

            if os.path.exists(m_dst):
                modules.append(m)

                if not filecmp.cmp(m_src, m_dst):
                    needUpdate = True

        if not needUpdate:
            return None

        files = []

        for f in hcjFiles:
            # optimization
            if os.path.basename(f) in MODULES:
                continue

            path = appDir / f
            if path.exists() and self.isTemplateBasedFile(path):
                files.append(f)

        # update media folder too
        if len(files):
            files.append('media')

        info = {
            'modules': modules,
            'files': files
        }

        return info

    def getExtAppsDir(self):
        extAppsDir = pathlib.Path(self.amSettings['extAppsDirectory'])
        if extAppsDir.is_absolute() and extAppsDir.is_dir():
            return extAppsDir
        else:
            return None

    def findApp(self, name, pathOnly=False):
        dirsToSearch = [self.getRootDir(True) / APPS]

        extAppsDir = self.getExtAppsDir()
        if extAppsDir:
            dirsToSearch.append(extAppsDir)

        # for security reasons
        name = pathlib.Path(name).name

        for appsDir in dirsToSearch:
            appDir = appsDir / name
            if appDir.is_dir():
                if pathOnly:
                    return appDir
                else:
                    return self.appInfo(appDir, appsDir)

        return None

    def isFileHidden(self, path):
        return (path.name.startswith('.') or
                APP_DATA_DIR in path.parts or
                BACKUP_LIBRARY_DIR in path.parts)

    def findApps(self):
        apps = []

        dirsToSearch = [self.getRootDir(True) / APPS]

        extAppsDir = self.getExtAppsDir()
        if extAppsDir:
            dirsToSearch.append(extAppsDir)

        for appsDir in dirsToSearch:
            for apppath in sorted(pathlib.Path(appsDir).iterdir()):
                if apppath.is_dir() and not self.isFileHidden(apppath):
                    apps.append(self.appInfo(apppath, appsDir))

        return apps

    def listFilesRel(self, allPaths, pattern, relativePath):
        paths = []

        for p in allPaths:
            if p.match(pattern) and not self.isFileHidden(p):
                pr = str(p.relative_to(relativePath))
                paths.append(pr)

        return sorted(paths)

    def appInfo(self, appDir, appsDir):
        # NOTE: for non-pathlib paths
        appDir = pathlib.Path(appDir)
        appsDir = pathlib.Path(appsDir)

        appDirRel = appDir.relative_to(appsDir)

        logicXML = appDirRel / LOGIC_XML

        if (appsDir / logicXML).exists():
            logicJS = appDirRel / LOGIC_JS
        else:
            logicJS = ''

        urlPrefix = self.pathToUrl(appsDir.name, makeAbs=True) + '/'

        isExt = not appsDir.samefile(self.getRootDir(True) / APPS)
        if isExt:
            urlPrefix = '/ext' + urlPrefix

        appFiles = list(appDir.rglob('*.*'))
        # typical node_modules directory can be quite big and it's not needed anyway
        appFiles = [p for p in appFiles if 'node_modules' not in p.parts]

        return {
            'name' : appDir.name,
            'title' : appDir.name.replace('_', ' ').title(),
            'appDir': appDir.resolve(),
            'appsDir': appsDir.resolve(),
            'path' : str(appDirRel),
            'urlPrefix': urlPrefix,
            'html' : self.listFilesRel(appFiles, '*.html', appsDir),
            'blend' : self.listFilesRel(appFiles, '*.blend', appsDir),
            'max' : self.listFilesRel(appFiles, '*.max', appsDir),
            'maya' : (self.listFilesRel(appFiles, '*.ma', appsDir) +
                      self.listFilesRel(appFiles, '*.mb', appsDir)),
            'gltf' : (self.listFilesRel(appFiles, '*.gltf', appsDir) +
                      self.listFilesRel(appFiles, '*.glb', appsDir)),
            'logicXML': str(logicXML),
            'logicJS': str(logicJS),
            'updateInfo': self.genUpdateInfo(appDir,
                    self.listFilesRel(appFiles, '*.html', appDir) +
                    self.listFilesRel(appFiles, '*.js', appDir) +
                    self.listFilesRel(appFiles, '*.css', appDir))
        }

    def isPuzzlesBasedFile(self, path):
        """absolute path"""

        # latin_1 fixes issues with forbidden utf-8 characters
        with open(path, 'r', encoding='latin_1') as f:
            content = f.read()
            if '__V3D_PUZZLES__' in content:
                return True
            # COMPAT: < 2.10
            if '__VERGE3D_PLAYER__' in content:
                return True

        return False

    def isTemplateBasedFile(self, path):
        """absolute path"""

        # NOTE: for non-pathlib paths
        path = pathlib.Path(path)

        if path.is_file():
            # latin_1 fixes issues with forbidden utf-8 characters
            with open(path, 'r', encoding='latin_1') as f:
                content = f.read()
                if '__V3D_TEMPLATE__' in content:
                    return True
                # COMPAT: < 2.10
                if '__VERGE3D_PLAYER__' in content:
                    return True

        return False


    def checksum(self, s):
        if len(s) != KEY_LEN:
            return False

        sum = 0
        for i in range(len(s) - 4):
            sum = sum + ord(s[i])

        hash1 = sum % HASH_SIZE
        hash2 = int(s[len(s)-4 : ], 16)

        return hash1 == hash2

    def getAnonymousTrialKey(self):

        print('Receiving anonymous trial license key')

        context = ssl.create_default_context()

        # HACK: workaround for SSLCertVerificationError in python 3.7
        pyVer = sys.version_info
        if pyVer[0] >= 3 and pyVer[1] >= 7:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

        # HACK: import it here to prevent strange issue with BlenderKit
        import http.client
        conn = http.client.HTTPSConnection(AUTH_ADDRESS, AUTH_PORT, context=context)

        try:
            conn.request('GET', '/get_anon_key')
            resp = conn.getresponse()
        except:
            print('GET /get_anon_key Connection refused')
            return None

        if resp.status == 200:
            key = resp.read().decode()

            self.amSettings['licenseKey'] = key
            self.amSettings['licenseKeyVersion'] = self.getLicenseInfo()['releaseVersion']

            self.saveSettings()
            print('Key:', key)
            return key
        else:
            print('GET /get_anon_key', resp.status, resp.reason)
            return None

    def getKeyTypeChar(self, key):
        return key[len(key)-14]

    def checkKeyModPackage(self, key):
        typechar = self.getKeyTypeChar(key)

        if self.modPackage == 'BLENDER' and typechar in ['1', '2', '3']:
            return True
        elif self.modPackage == 'MAX' and typechar in ['4', '5', '6']:
            return True
        elif self.modPackage == 'MAYA' and typechar in ['7', '8', '9']:
            return True
        elif typechar == 'a':
            return True
        else:
            return False

    def replaceEngineKey(self, path, key):
        v3dlmatch = re.compile('__V3DL__[a-fA-F0-9]{10,10}')
        v3dlnew = '__V3DL__' + key[0:10]

        lines = None

        with open(path, 'r',  encoding='utf-8') as fin:
            lines = fin.readlines()

        with open(path, 'w',  encoding='utf-8') as fout:
            for line in lines:
                fout.write(v3dlmatch.sub(v3dlnew, line))

    def getLicenseInfo(self, key=None):
        info = {
            'type': 'TRIAL',
            'modPackage': '',
            'keyExists': False,
            'keyHash': None,
            'validUntil': None,
            'maintenance': False,
            'renewalGracePeriod': 0,
            'releaseVersion': '',
            'releaseDate': None
        }

        try:
            with open(join(BASE_DIR, '..', 'package.json'), 'r', encoding='utf-8') as f:
                package = json.load(f)
                info['releaseVersion'] = package['version']
                info['releaseDate'] = datetime.datetime.strptime(package['date'], "%Y-%m-%d")
        except OSError:
            pass

        # get from file
        if key == None:
            key = self.amSettings['licenseKey'].strip()

        if key and self.checksum(key):
            info['keyExists'] = True

            # generate key hash
            h = hashlib.sha1()
            h.update(key.encode())
            info['keyHash'] = h.hexdigest()

            # parse key info
            typechar = self.getKeyTypeChar(key)
            delta = 0

            if typechar == '0':
                info['type'] = 'TRIAL'
                delta = datetime.timedelta(days=30)
            else:
                if typechar == '1':
                    info['type'] = 'FREELANCE'
                    info['modPackage'] = 'BLENDER'
                if typechar == '2':
                    info['type'] = 'TEAM'
                    info['modPackage'] = 'BLENDER'
                if typechar == '3':
                    info['type'] = 'ENTERPRISE'
                    info['modPackage'] = 'BLENDER'
                if typechar == '4':
                    info['type'] = 'FREELANCE'
                    info['modPackage'] = 'MAX'
                if typechar == '5':
                    info['type'] = 'TEAM'
                    info['modPackage'] = 'MAX'
                if typechar == '6':
                    info['type'] = 'ENTERPRISE'
                    info['modPackage'] = 'MAX'
                if typechar == '7':
                    info['type'] = 'FREELANCE'
                    info['modPackage'] = 'MAYA'
                if typechar == '8':
                    info['type'] = 'TEAM'
                    info['modPackage'] = 'MAYA'
                if typechar == '9':
                    info['type'] = 'ENTERPRISE'
                    info['modPackage'] = 'MAYA'
                if typechar == 'a':
                    info['type'] = 'ULTIMATE'
                    info['modPackage'] = 'ALL'
                delta = datetime.timedelta(days=365)

                info['maintenance'] = True

            unix = int(key[len(key)-13 : len(key)-4], 16)

            dt = datetime.datetime.utcfromtimestamp(unix)

            info['validUntil'] = dt + delta

            if info['validUntil'] < info['releaseDate']:
                info['type'] = 'OUTDATED'
                info['maintenance'] = False

            now = datetime.datetime.now()
            if now > info['validUntil']:
                info['maintenance'] = False
                renewalDelta = datetime.timedelta(days=30) - (now - info['validUntil'])
                info['renewalGracePeriod'] = max(0, renewalDelta.days)

        return info

    def copyTemplateTree(self, src, dst, appName, modPackSubDir):
        names = os.listdir(src)
        errors = []

        # do not crash on already created app dir
        if not os.path.exists(dst):
            os.mkdir(dst)

        for name in names:
            srcname = join(src, name)

            try:
                if os.path.isdir(srcname):
                    if name not in ['blender', 'max', 'maya']:
                        self.copyTemplateTree(srcname, join(dst, name), appName, modPackSubDir)
                    elif name == modPackSubDir or (name == 'blender' and modPackSubDir == 'all'):

                        if modPackSubDir == 'all':
                            # Max, Maya, then Blender
                            self.copyTemplateTree(join(src, 'max'), dst, appName, modPackSubDir)
                            self.copyTemplateTree(join(src, 'maya'), dst, appName, modPackSubDir)

                        # copy modelling package assets to upper dir
                        self.copyTemplateTree(srcname, dst, appName, modPackSubDir)

                else:
                    dstname = join(dst, name.replace('template', appName))
                    shutil.copy2(srcname, dstname)
            except OSError as why:
                errors.append((srcname, join(dst, name), str(why)))
            except shutil.Error as err:
                errors.extend(err.args[0])

        if errors:
            raise shutil.Error(errors)

    def backupFile(self, path, backupDir):
        # NOTE: for non-pathlib paths
        path = pathlib.Path(path)

        # nothing to backup
        if not path.is_file():
            return

        backupDir = pathlib.Path(backupDir)

        print('Backup {}'.format(path.name))

        if not backupDir.exists():
            backupDir.mkdir(parents=True)

        now = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        shutil.copyfile(path, backupDir / (path.stem + '_' + now + path.suffix))

    def copyAppTemplate(self, appDir, tplName, modPackage, modules):

        appName = os.path.basename(appDir)
        appTplDir = join(BASE_DIR, 'templates', tplName)

        if not os.path.exists(appTplDir):
            return

        self.copyTemplateTree(appTplDir, appDir, appName, modPackage.lower())

        htmlPath = join(appDir, appName + '.html')
        # may be omitted in user template
        if os.path.exists(htmlPath):
            self.replaceTemplateStrings(htmlPath, 'template.', appName + '.')

            if 'v3d.legacy.js' in modules:
                self.replaceTemplateStrings(htmlPath, 'v3d.js', 'v3d.legacy.js')

            modulesCode = ''

            if 'webxr-polyfill.js' in modules:
                modulesCode += '  <script src="webxr-polyfill.js"></script>\n'
                modulesCode += '  <script>var polyfill = new WebXRPolyfill();</script>\n'

            # prioritize wasm modules if both versions are present
            if 'ammo.wasm.js' in modules:
                modulesCode += '  <script src="ammo.wasm.js"></script>\n'
            elif 'ammo.js' in modules:
                modulesCode += '  <script src="ammo.js"></script>\n'

            self.replaceTemplateStrings(htmlPath, '<!-- __V3D_COMPAT_MODULES__ -->', modulesCode)

            version = self.getLicenseInfo()['releaseVersion']
            # remove version suffix to simply template merging
            version = re.findall('\d*\.\d*\.?\d*', version)[0]
            metaCode = '<meta name="generator" content="Verge3D {0}">'.format(version)
            self.replaceTemplateStrings(htmlPath, '<!-- __V3D_META__ -->', metaCode)

        jsPath = join(appDir, appName + '.js')
        # may be omitted in user template
        if os.path.exists(jsPath):
            self.replaceTemplateStrings(jsPath, 'template.gltf', appName + '.gltf')

        gltfPath = join(appDir, appName + '.gltf')
        # may be omitted in user template
        if os.path.exists(gltfPath):
            self.replaceTemplateStrings(gltfPath, 'template.bin', appName + '.bin')

        indexPath = join(appDir, 'index.html')
        # may be omitted in user template
        if os.path.exists(indexPath):
            self.replaceTemplateStrings(indexPath, 'template.html', appName + '.html')

        # copy modules from build dir (+preserve modification time)
        for mod in modules:
            mSrc = join(BASE_DIR, '..', 'build', mod)
            mDst = join(appDir, mod)
            shutil.copyfile(mSrc, mDst)
            shutil.copystat(mSrc, mDst)

        self.genTemplateMetadata(appDir, tplName)

    def genTemplateMetadata(self, appDir, tplName):

        tplData = {
            'name': tplName,
            'files': {}
        }

        for f in list(appDir.rglob('*.*')):

            with open(f, 'rb') as fp:
                content = fp.read()

                h = hashlib.sha1()
                h.update(content)

                fileData = {
                    'hash': h.hexdigest()
                };

                if f.suffix in ['.html', '.css', '.js'] and f.name != 'v3d.js' and f.name != 'v3d.legacy.js' and self.isTemplateBasedFile(f):
                    fileData['type'] = 'ASCII'
                    fileData['content'] = base64.b64encode(content).decode('utf-8')
                else:
                    fileData['type'] = 'BINARY'

                tplData['files'][str(f.relative_to(appDir))] = fileData

        appDataDir = appDir / APP_DATA_DIR

        if not appDataDir.exists():
            appDataDir.mkdir()

        with open(appDataDir / APP_TEMPLATE_JSON, 'w', encoding='utf-8') as f:
            json.dump(tplData, f, sort_keys=True, indent=4, separators=(', ', ': '), ensure_ascii=False)

    def replaceTemplateStrings(self, path, pattern, replacement='', count=0):
        """
        A: Replace 'pattern' to 'replacement'
        B: Render template with 'pattern' substitution using Mako Template class
        """

        content = None

        with open(path, 'r',  encoding='utf-8') as fin:
            content = fin.read()

        if type(pattern) == str:
            if count:
                content = content.replace(pattern, replacement, count)
            else:
                content = content.replace(pattern, replacement)
        else:
            content = Template(content).render_unicode(**pattern)

        with open(path, 'w',  encoding='utf-8') as fout:
            fout.write(content)

    def getS3Credentials(self):
        import json

        licenseInfo = self.getLicenseInfo()

        # try to receive anonymous key
        if not licenseInfo['keyExists'] and self.getAnonymousTrialKey():
            licenseInfo = self.getLicenseInfo()

        if not licenseInfo['keyExists']:
            return None

        context = ssl.create_default_context()

        # HACK: workaround for SSLCertVerificationError in python 3.7
        pyVer = sys.version_info
        if pyVer[0] >= 3 and pyVer[1] >= 7:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

        # HACK: import it here to prevent strange issue with BlenderKit
        import http.client
        conn = http.client.HTTPSConnection(AUTH_ADDRESS, AUTH_PORT, context=context)

        try:
            conn.request('GET', '/get_credentials?hash=%s' % licenseInfo['keyHash'])
            resp = conn.getresponse()
        except:
            print('GET /get_credentials Connection refused')
            return None

        if resp.status == 200:
            return json.loads(resp.read().decode())
        else:
            print('GET /get_credentials', resp.status, resp.reason)
            return None

    def sortHTMLs(self, appName, files):
        """index files come first"""

        indices = []
        main = []
        other = []

        for f in files:
            if 'index.htm' in f:
                indices.append(f)
            elif self.checkMainFile(appName, f, files):
                main.append(f)
            else:
                other.append(f)

        return indices + main + other

    def checkMainFile(self, appName, file, files):
        import difflib

        for f in files:
            if (difflib.SequenceMatcher(None, os.path.basename(f), appName).ratio() >
                    difflib.SequenceMatcher(None, os.path.basename(file), appName).ratio()):
                return False

        return True

    def findMainFile(self, appName, files):
        import difflib

        mainFile = files[0]

        for f in files:
            if (difflib.SequenceMatcher(None, os.path.basename(f), appName).ratio() >
                    difflib.SequenceMatcher(None, os.path.basename(mainFile), appName).ratio()):
                mainFile = f

        return mainFile

    def manageURL(self, app):
        return '/manage/?app={0}'.format(urllib.parse.quote(app))

    def genAppViewInfo(self, app):
        rootDir = self.getRootDir()

        urlPrefix = app['urlPrefix']

        appViewInfo = {
            'name' : app['name'],
            'title' : app['title'],
            'url': urlPrefix + self.pathToUrl(app['path']),
            'manageURL': self.manageURL(app['name']),
            'html': [],
            'gltf': [],
            'blend': [],
            'max': [],
            'maya': [],
            'puzzles': None,
            'needsUpdate': False
        }

        # NONE, HTML (copied player), GLTF (linked player)
        logicType = 'NONE'

        playerBasedHTMLs = []

        for html in self.sortHTMLs(app['name'], app['html']):
            if self.isPuzzlesBasedFile(join(app['appsDir'], html)):
                logicType = 'HTML'
                playerBasedHTMLs.append(html)

            appViewInfo['html'].append({'name': os.path.basename(html),
                                        'path': html,
                                        'url': urlPrefix + self.pathToUrl(html)})

        appHasHTML = bool(len(app['html']))

        if logicType != 'HTML' and not appHasHTML and len(app['gltf']):
            logicType = 'GLTF'

        for gltf in app['gltf']:

            if not appHasHTML and self.checkMainFile(app['name'], gltf, app['gltf']):
                logicJS = app['logicJS']
            else:
                logicJS = ''

            url = '/player/player.html?load=..' + urlPrefix + self.pathToUrl(gltf)
            if len(logicJS) > 0:
                url += '&logic=..' + urlPrefix + self.pathToUrl(logicJS)

            appViewInfo['gltf'].append({'name': os.path.basename(gltf),
                                        'path': gltf,
                                        'url': url})

        for blend in app['blend']:
            if logicType == 'HTML':
                isMain = self.checkMainFile(app['name'], blend, app['blend'])
            else:
                isMain = False

            appViewInfo['blend'].append({'name': os.path.basename(blend),
                                         'path': blend,
                                         'url': urlPrefix + self.pathToUrl(blend),
                                         'isMain': isMain })

        for maxx in app['max']:
            if logicType == 'HTML':
                isMain = self.checkMainFile(app['name'], maxx, app['max'])
            else:
                isMain = False

            appViewInfo['max'].append({'name': os.path.basename(maxx),
                                       'path': maxx,
                                       'url': urlPrefix + self.pathToUrl(maxx),
                                       'isMain': isMain })

        for maya in app['maya']:
            if logicType == 'HTML':
                isMain = self.checkMainFile(app['name'], maya, app['maya'])
            else:
                isMain = False

            appViewInfo['maya'].append({'name': os.path.basename(maya),
                                        'path': maya,
                                        'url': urlPrefix + self.pathToUrl(maya),
                                        'isMain': isMain })

        # move main assets to front
        for assetType in ['blend', 'max', 'maya']:
            for i in range(len(appViewInfo[assetType])):
                asset = appViewInfo[assetType][i]
                if asset['isMain']:
                    appViewInfo[assetType].insert(0, appViewInfo[assetType].pop(i))
                    break

        logicExists = bool(app['logicJS'])

        if logicType == 'HTML':
            '''
            NOTE: for now only HTML files that lie in the app's root work with
            puzzles, non-root HTML files have some path issues (404)
            '''
            playerBasedHTMLsInRoot = [htmlPath for htmlPath in playerBasedHTMLs
                    if len(os.path.normpath(htmlPath).split(os.path.sep)) == 2]

            if len(playerBasedHTMLsInRoot) > 0:
                mainHTML = self.findMainFile(app['name'], playerBasedHTMLsInRoot)

                url = urlPrefix + self.pathToUrl(mainHTML)
                url += '?logic=' + self.pathToUrl(os.path.basename(app['logicXML']))
                url += '&theme=' + self.amSettings['theme']

                appViewInfo['puzzles'] = {'url': url,
                                        'logicExists': logicExists}

        elif logicType == 'GLTF':
            mainGLTF = self.findMainFile(app['name'], app['gltf'])

            url = '/player/player.html?load=..' + urlPrefix + self.pathToUrl(mainGLTF)
            url += '&logic=..' + urlPrefix + self.pathToUrl(app['logicXML'])
            url += '&theme=' + self.amSettings['theme']

            appViewInfo['puzzles'] = {'url': url,
                                      'logicExists': logicExists}

        if app['updateInfo']:
            appViewInfo['needsUpdate'] = True

        return appViewInfo

    def updateApp(self, appInfo, modules, files):
        appDir = appInfo['appDir']

        print('Updating application: {}'.format(appInfo['name']))

        appDataDir = appDir / APP_DATA_DIR

        if not appDataDir.exists():
            appDataDir.mkdir()

        tplData = None

        try:
            with open(appDataDir / APP_TEMPLATE_JSON, 'r', encoding='utf-8') as f:
                tplData = json.load(f)
        except OSError:
            pass

        if tplData and 'name' in tplData:
            templateName = tplData['name']
        else:
            templateName = 'Standard Light'

        templateAppName = os.path.basename(appDir)

        # NOTE: use similar-to-app name HTML name instead of updated app name
        # this resolves updating issues with renamed apps
        templateFiles = list(filter(lambda f: os.path.isfile(join(appDir, f)) and
                                    self.isTemplateBasedFile(join(appDir, f)), files))
        if len(templateFiles):
            templateAppName = os.path.splitext(self.findMainFile(os.path.basename(appDir), templateFiles))[0]

        with tempfile.TemporaryDirectory() as td:
            tmpAppDir = pathlib.Path(td) / templateAppName
            tmpAppDir.mkdir()

            # this method will fail first if the verge3d dir is read-only
            try:
                self.copyAppTemplate(tmpAppDir, templateName, self.modPackage, modules)
            except PermissionError:
                self.writeError(ACCESS_DENIED_MSG)
                return

            for m in modules:
                mSrc = tmpAppDir / m
                mDst = appDir / m

                if not mDst.exists() or not filecmp.cmp(mSrc, mDst):
                    print('Updating app module {0}'.format(m))
                    shutil.copyfile(mSrc, mDst)

                shutil.copystat(mSrc, mDst)

            for f in files:

                if f == 'media':
                    mediaSrcDir = tmpAppDir / 'media'
                    mediaDstDir = appDir / 'media'

                    if not mediaDstDir.exists():
                        mediaDstDir.mkdir()

                    for item in os.listdir(mediaSrcDir):
                        src = mediaSrcDir / item
                        dst = mediaDstDir / item

                        if not dst.exists() or not filecmp.cmp(src, dst):
                            self.backupFile(dst, appDataDir / BACKUP_UPDATE_DIR)
                            print('Updating media file {0}'.format(item))
                            shutil.copyfile(src, dst)

                else:
                    ext = os.path.splitext(f)[1]

                    src = tmpAppDir / (os.path.basename(tmpAppDir)+ext)
                    dst = appDir / f

                    if not dst.exists() or not filecmp.cmp(src, dst):
                        self.backupFile(dst, appDataDir / BACKUP_UPDATE_DIR)

                        print('Updating app file {0}'.format(f))

                        if tplData and f in tplData['files'] and tplData['files'][f]['type'] == 'ASCII':
                            print('Performing 3-way merge... ', end='')

                            tmpFile = tempfile.NamedTemporaryFile('wb', delete=False)
                            tmpFile.write(base64.b64decode(tplData['files'][f]['content']))
                            tmpFile.close()

                            pythonPath = sys.executable

                            # COMPAT: for Blender <3.0 binary_path_python used instead of incorrect sys.executable
                            try:
                                import bpy
                                pythonPath = bpy.app.binary_path_python
                            except ImportError:
                                pass
                            except AttributeError:
                                pass

                            dstStr = self.runPython([join(BASE_DIR, 'lib', 'merge3.py'),
                                                     str(dst), tmpFile.name, str(src)])
                            if '<<<<<<<' not in dstStr.decode('utf-8'):
                                with open(dst, 'wb') as f:
                                    f.write(dstStr)
                                print('success!')
                            else:
                                print('conflict, overwriting...')
                                shutil.copyfile(src, dst)
                        else:
                            shutil.copyfile(src, dst)

            # TODO: need more precise way to update the source files for 3-way merging
            if len(files):
                shutil.copyfile(tmpAppDir / APP_DATA_DIR / APP_TEMPLATE_JSON, appDataDir / APP_TEMPLATE_JSON)


    # server sub-classes

    class ResponseTemplates(object):
        def getJSContext(self):
            server = self.settings['server']

            licenseInfo = server.getLicenseInfo();

            jsContext = {
                'version': licenseInfo['releaseVersion'],
                'package': server.modPackage.title(),
                'releaseDate': str(licenseInfo['releaseDate'].date()),
                'checkForUpdates': server.amSettings['checkForUpdates']
            }

            return jsContext

        def renderTemplate(self, template, substitution):

            tplLookup = TemplateLookup(directories=[join(BASE_DIR, 'ui')],
                                       input_encoding='utf-8',
                                       output_encoding='utf-8',
                                       encoding_errors='replace')

            server = self.settings['server']
            tplOut = tplLookup.get_template(template).render_unicode(**substitution)

            return tplOut

        def writeError(self, message, dialog=True):
            if dialog:
                self.write(self.renderTemplate('dialog_error.tpl', {
                    'message': message
                }))
            else:
                self.write(self.renderTemplate('error.tpl', {
                    'message': message,
                    'jsContext': self.getJSContext()
                }))

    class RootHandler(tornado.web.RequestHandler, ResponseTemplates):
        #@profile(immediate=True)
        def get(self):
            server = self.settings['server']
            server.loadSettings()

            rootDir = server.getRootDir()

            try:
                apps = server.findApps()
            except FileNotFoundError:
                self.writeError('No applications directory found!', False)
                return
            except PermissionError:
                self.writeError('Access is denied. Make sure that you have permissions to read ' +
                                'from Verge3D installation directory.', False)
                return

            appsViewInfo = []

            for app in apps:
                # ignore stock apps, if needed
                if (server.amSettings['hideStockApps'] and
                    app['appDir'].name in server.amSettings['stockApps']):
                    continue

                appsViewInfo.append(server.genAppViewInfo(app))

            self.write(self.renderTemplate('main.tpl', {
                'apps': appsViewInfo,
                'appTemplates': server.amSettings['appTemplates'],
                'theme': server.amSettings['theme'],
                'licenseInfo': server.getLicenseInfo(),
                'package': server.modPackage,
                'jsContext': self.getJSContext()
            }))

    class OpenFileHandler(tornado.web.RequestHandler, ResponseTemplates):
        def get(self):
            try:
                filepath = self.get_argument('filepath')
            except tornado.web.MissingArgumentError:
                self.write('Specify file name')

            server = self.settings['server']

            path = str(server.resolveURLPath(filepath))

            if sys.platform.startswith('darwin'):
                if os.path.isdir(path):
                    subprocess.call(('open', path))
                else:
                    subprocess.call(('open', '-n', path))
            elif os.name == 'nt':
                # ignore not-found errors
                try:
                    os.startfile(path)
                except:
                    pass
            elif os.name == 'posix':
                subprocess.call(('xdg-open', path))

            self.write('ok')

    class DeleteConfirmHandler(tornado.web.RequestHandler, ResponseTemplates):
        def get(self):
            try:
                app = self.get_argument('app')
            except tornado.web.MissingArgumentError:
                self.writeError('Please specify app to delete')
                return

            server = self.settings['server']

            appInfo = server.findApp(app)

            if not appInfo:
                self.writeError('Could not find app: {0}.'.format(app))
                return

            self.write(self.renderTemplate('dialog_delete_confirm.tpl', {
                'app': app,
                'manageURL': server.manageURL(app),
                'title': appInfo['title']
            }))

    class DeleteFileHandler(tornado.web.RequestHandler, ResponseTemplates):
        def get(self):
            try:
                app = self.get_argument('app')
            except tornado.web.MissingArgumentError:
                self.writeError('Please specify app to delete')
                return

            server = self.settings['server']

            appInfo = server.findApp(app)
            if not appInfo:
                self.writeError('Could not find app: {0}.'.format(app))
                return

            appDir = appInfo['appDir']

            try:
                send2trash.send2trash(str(appDir))
            except:
                self.writeError('Could not delete app folder.')
                return

            self.write(self.renderTemplate('dialog_delete_done.tpl', {
                'title': appInfo['title']
            }))


    class CreateAppHandler(tornado.web.RequestHandler, ResponseTemplates):

        def post(self):
            try:
                name = self.get_argument('app_name')
                nameDisp = self.get_argument('app_name_disp')
            except tornado.web.MissingArgumentError:
                self.writeError('Please specify App name')
                return

            if re.search('[/\\\\]', name):
                self.writeError('App name contains invalid characters. Please try another name.')
                return

            try:
                tplName = self.get_argument('template_name')
            except tornado.web.MissingArgumentError:
                self.writeError('Please specify App template name')
                return

            server = self.settings['server']

            try:
                copyOpentypeModule = server.argBool(self.get_argument('copy_opentype_module'))
            except tornado.web.MissingArgumentError:
                copyOpentypeModule = False

            try:
                copyIE11Module = server.argBool(self.get_argument('copy_ie11_module'))
            except tornado.web.MissingArgumentError:
                copyIE11Module = False

            try:
                copyARVRModule = server.argBool(self.get_argument('copy_ar_vr_module'))
            except tornado.web.MissingArgumentError:
                copyARVRModule = False

            try:
                copyPhysicsModule = server.argBool(self.get_argument('copy_physics_module'))
            except tornado.web.MissingArgumentError:
                copyPhysicsModule = False

            if name == '':
                self.writeError('Please specify a name for your application.')
                return

            extAppsDir = server.getExtAppsDir()
            if extAppsDir:
                appDir = extAppsDir / name
            else:
                appDir = server.getRootDir(True) / APPS / name

            try:
                os.mkdir(appDir)
            except FileExistsError:
                status = 'Application <a href="/manage/?app=' + name + '" class="colored-link">' + nameDisp
                status += '</a> already exists. Either remove it first, or try another name.'
                self.writeError(status)
                return
            except PermissionError:
                self.writeError(ACCESS_DENIED_MSG)
                return

            modules = []

            if copyIE11Module:
                modules.append('v3d.legacy.js')
            else:
                modules.append('v3d.js')

            if copyOpentypeModule:
                modules.append('opentype.js')
            if copyARVRModule:
                modules.append('webxr-polyfill.js')

            if copyPhysicsModule:
                if copyIE11Module:
                    modules.append('ammo.js')
                else:
                    modules.append('ammo.wasm.js')
                    modules.append('ammo.wasm.wasm')

            server.copyAppTemplate(appDir, tplName, server.modPackage, modules)

            self.write(self.renderTemplate('dialog_new_app_created.tpl', {
                'nameDisp': nameDisp,
                'manageURL': server.manageURL(name)
            }))


    class ManageAppHandler(tornado.web.RequestHandler, ResponseTemplates):

        def get(self):
            try:
                app = self.get_argument('app')
            except tornado.web.MissingArgumentError:
                self.writeError('Please specify App name')
                return

            server = self.settings['server']
            server.loadSettings()

            appInfo = server.findApp(app)
            if not appInfo:
                self.writeError('Could not find app: {}.'.format(app))
                return

            appViewInfo = server.genAppViewInfo(appInfo)

            self.write(self.renderTemplate('manage.tpl', {
                'app': appViewInfo,
                'appTemplates': server.amSettings['appTemplates'],
                'theme': server.amSettings['theme'],
                'licenseInfo': server.getLicenseInfo(),
                'package': server.modPackage,
                'jsContext': self.getJSContext()
            }))

    class ProcessNetworkHandler(tornado.web.RequestHandler, ResponseTemplates):

        def writeS3Error(self, e, dialog=True):

            type = 'NET_ERR_UNKNOWN'
            error = ''

            # NOTE: S3 upload catch and replace botocore exceptions by this one
            if isinstance(e, boto3.exceptions.S3UploadFailedError):
                error = str(e)

                if 'RequestTimeTooSkewed' in error:
                    type = 'NET_ERR_TIME_SKEWED'
                    self.set_status(400)
                else:
                    self.set_status(500)

            elif isinstance(e, UploadCancelledException):
                type = 'NET_ERR_CANCELLED'
                self.set_status(200)

            elif isinstance(e, NothingToUploadException):
                type = 'NET_ERR_NOTHING'
                self.set_status(400)

            else:
                error = e.response['Error']['Code']

                if error == 'RequestTimeTooSkewed':
                    type = 'NET_ERR_TIME_SKEWED'
                    self.set_status(400)
                else:
                    self.set_status(500)

            if type != 'NET_ERR_UNKNOWN':
                message = type
            else:
                message = error

            if dialog:
                self.write(self.renderTemplate('dialog_error.tpl', {
                    'message': message
                }))
            else:
                self.write(self.renderTemplate('error.tpl', {
                    'message': message,
                    'jsContext': self.getJSContext()
                }))

        def uploadS3File(self, s3, credentials, path, relativeTo, urlPrefix='/'):
            """relative path, returns uploaded URL"""

            server = self.settings['server']

            if server.uploadCancelled:
                raise UploadCancelledException

            bucket = credentials['aws_bucket']
            userDir = credentials['aws_user_dir']

            # NOTE: need path-like URL prefix here
            urlPrefix = urllib.parse.unquote(urlPrefix)

            key = userDir + urlPrefix + server.pathToUrl(path, quote=False)

            print('Uploading:', bucket + '/' + key)

            # NOTE: force this mime instead of new 'model/gltf+json'
            # to enable CloudFront gzip compression
            if os.path.splitext(path)[1] == '.gltf':
                mime_type = 'application/json'
            else:
                mime_type = mimetypes.guess_type(key)[0]

            if not mime_type:
                mime_type = 'application/octet-stream'

            extra_args = {
                'ContentType': mime_type,
                'ACL': 'public-read',
                'CacheControl': 'max-age=' + str(server.amSettings['cacheMaxAge'] * 60)
            }
            s3.upload_file(join(relativeTo, path), bucket, key, ExtraArgs=extra_args)

            return CDN_HOST + key

        def uploadS3Dir(self, s3, credentials, dirRootRel):

            server = self.settings['server']

            rootDir = server.getRootDir()

            urls = []

            pathAbs = pathlib.Path(join(rootDir, norm(dirRootRel)))
            uploadList = list(pathAbs.rglob('*'))

            for p in uploadList:
                if p.is_dir():
                    continue

                # NOTE: workaround for some issue with emtpy files
                if p.lstat().st_size == 0:
                    continue

                urls.append(self.uploadS3File(s3, credentials, p.relative_to(rootDir), rootDir))

            return urls

        async def get(self, tail=None):
            server = self.settings['server']
            await server.runAsync(self.netRequestThread)

        def netRequestThread(self):

            server = self.settings['server']
            rootDir = server.getRootDir()

            req = self.get_argument('req')

            if req not in ALLOWED_NET_REQUESTS:
                self.set_status(400)
                self.writeError('Bad Verge3D Network request', False)
                return

            dialogMode = (req != 'status')

            if req == 'progress':
                self.write(str(server.uploadProgress))
                return

            elif req == 'cancel':
                server.uploadProgress = 100
                server.uploadCancelled = True
                return

            server.uploadProgress = 0
            server.uploadCancelled = False

            print('Requesting S3 credentials')

            cred = server.getS3Credentials()
            if not cred:
                self.set_status(502)
                self.writeError('Failed to receive Verge3D Network credentials, possibly due to connection error.',
                                dialogMode)
                return

            # Create an S3 client
            s3 = boto3.client('s3',
                aws_access_key_id = cred['aws_access_key_id'],
                aws_secret_access_key = cred['aws_secret_access_key'],
                aws_session_token = cred['aws_session_token'],
                # NOTE: fixes some issue with non-standard region
                config=botocore.client.Config(signature_version='s3v4'),
                # NOTE: fixes strange boto3 bug with non-standard region
                region_name = 'eu-central-1'
            )

            server.uploadProgress = 10

            bucket = cred['aws_bucket']
            userDir = cred['aws_user_dir']

            if req == 'status':
                prefix = userDir + '/'

                paginator = s3.get_paginator('list_objects_v2')
                pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

                keys = []
                keysSplit = []

                filesViewInfo = []

                maxDirLevels = 0

                try:
                    for page in pages:
                        if 'Contents' in page:
                            for obj in page['Contents']:
                                key = obj['Key']
                                keys.append(key)
                                keysSplit.append(key.split('/'))
                                maxDirLevels = max(maxDirLevels, len(keysSplit[-1]))

                        processedDirs = []

                        for level in range(maxDirLevels):
                            for key in keysSplit:
                                if level < len(key) - 1:
                                    dir = '/'.join(key[0:level+1])
                                    dir += '/'

                                    if not (dir in processedDirs):
                                        processedDirs.append(dir)

                        keys += processedDirs
                        keys.sort()

                        for key in keys:

                            path = key.replace(prefix, '/').rstrip('/')

                            isDir = (key[-1] == '/')
                            indent = len(path.split('/')) - 1
                            url = '' if isDir else (CDN_HOST + server.pathToUrl(key, replaceBackslash=False))

                            fileViewInfo = {
                                'name': os.path.basename(path),
                                'isDir': isDir,
                                'indent': indent,
                                'key': server.pathToUrl(key, replaceBackslash=False),
                                'url': url
                            }

                            filesViewInfo.append(fileViewInfo)
                except botocore.exceptions.ClientError as e:
                    self.writeS3Error(e, dialogMode)
                    return
                except AttributeError:
                    # HACK: workaround for boto3 issue in Python3.9
                    self.writeError('NET_ERR_TIME_SKEWED', dialogMode)
                    return

                self.write(self.renderTemplate('network.tpl', {
                    'filesViewInfo': filesViewInfo,
                    'appTemplates': server.amSettings['appTemplates'],
                    'theme': server.amSettings['theme'],
                    'licenseInfo': server.getLicenseInfo(),
                    'package': server.modPackage,
                    'jsContext': self.getJSContext()
                }))

                server.uploadProgress = 100

            elif req == 'delete':

                keys = self.get_arguments('key')

                if not len(keys) or keys[0] == '':
                    self.writeError('No files selected for deletion.')
                    self.set_status(400)
                    return

                delete_keys = {'Objects' : []}

                for key in keys:
                    print('Removing key: ' + key)
                    delete_keys['Objects'].append({'Key' : key})

                try:
                    resp = s3.delete_objects(Bucket=bucket, Delete=delete_keys)
                except botocore.exceptions.ClientError as e:
                    self.writeS3Error(e)
                    return

                self.write(self.renderTemplate('dialog_network_delete.tpl', {
                    'numFiles': str(len(keys))
                }))

                server.uploadProgress = 100

            elif req == 'upload':

                self.processUploadRequest(s3, cred)


        def processUploadRequest(self, s3, cred):

            server = self.settings['server']
            rootDir = server.getRootDir(True)

            appInfo = server.findApp(self.get_argument('app'))
            if not appInfo:
                self.writeError('Could not find app folder.')
                return

            appDir = appInfo['appDir']
            appsDir = appInfo['appsDir']
            urlPrefix = appInfo['urlPrefix']

            isZip = bool(int(self.get_argument('zip')))

            uploadList = []
            hasEngine = False

            for p in list(appDir.rglob('*')):
                if p.is_dir():
                    continue

                # NOTE: workaround for some issue with emtpy files
                if p.lstat().st_size == 0:
                    continue

                ignore = False

                if not isZip and not server.amSettings['uploadSources']:
                    for pattern in CDN_IGNORE:
                        if p.match(pattern):
                            ignore = True
                            break

                if ignore:
                    continue

                uploadList.append(p)

                if p.name == 'v3d.js' or p.name == 'v3d.legacy.js':
                    hasEngine = True

            if not len(uploadList):
                self.writeS3Error(NothingToUploadException())
                return

            htmlLinks = []

            if isZip:
                zipDir = rootDir / 'zip'

                if not zipDir.exists():
                    zipDir.mkdir()

                zipPath = rootDir / 'zip' / (appDir.name + '.zip')

                with zipfile.ZipFile(zipPath, 'w', compression=zipfile.ZIP_DEFLATED) as appzip:
                    for p in uploadList:
                        appzip.write(p, p.relative_to(appInfo['appsDir']))

                try:
                    url = self.uploadS3File(s3, cred, zipPath.relative_to(rootDir), rootDir)
                except boto3.exceptions.S3UploadFailedError as e:
                    self.writeS3Error(e)
                    return
                except AttributeError:
                    # HACK: workaround for boto3 issue in Python3.9
                    self.writeError('NET_ERR_TIME_SKEWED')
                    return
                except UploadCancelledException as e:
                    self.writeS3Error(e)
                    return

                htmlLinks.append(url)

                shutil.rmtree(zipDir)
            else:
                progressInc = 90 / len(uploadList)

                for p in uploadList:

                    try:
                        url = self.uploadS3File(s3, cred, p.relative_to(appsDir), appsDir, urlPrefix)
                    except boto3.exceptions.S3UploadFailedError as e:
                        self.writeS3Error(e)
                        return
                    except AttributeError:
                        # HACK: workaround for boto3 issue in Python3.9
                        self.writeError('NET_ERR_TIME_SKEWED')
                        return
                    except UploadCancelledException as e:
                        self.writeS3Error(e)
                        return

                    if p.suffix == '.html':
                        htmlLinks.append(url)

                    server.uploadProgress += progressInc

            # shared engine may be needed for some HTMLs/GLTFs
            if not isZip and not hasEngine and (len(htmlLinks) or len(appInfo['gltf'])):
                server.uploadProgress = 93
                try:
                    # TODO: need proper evaluation of required modules
                    self.uploadS3File(s3, cred, join('build', 'v3d.js'), rootDir)
                    self.uploadS3File(s3, cred, join('build', 'v3d.legacy.js'), rootDir)
                    self.uploadS3File(s3, cred, join('build', 'webxr-polyfill.js'), rootDir)
                except boto3.exceptions.S3UploadFailedError as e:
                    self.writeS3Error(e)
                    return
                except UploadCancelledException as e:
                    self.writeS3Error(e)
                    return

            # pure player/gltf app
            if not isZip and not len(htmlLinks) and len(appInfo['gltf']):

                server.uploadProgress = 95

                try:
                    player_url = self.uploadS3File(s3, cred, join('player', 'player.html'), rootDir)
                except boto3.exceptions.S3UploadFailedError as e:
                    self.writeS3Error(e)
                    return
                except UploadCancelledException as e:
                    self.writeS3Error(e)
                    return

                for gltf in appInfo['gltf']:
                    gltf_link = player_url + '?load=..' + appInfo['urlPrefix'] + server.pathToUrl(gltf)
                    if appInfo['logicJS']:
                        gltf_link += '&logic=..' + appInfo['urlPrefix'] + server.pathToUrl(appInfo['logicJS'])

                    htmlLinks.append(gltf_link)

                try:
                    self.uploadS3File(s3, cred, join('player', 'player.js'), rootDir)
                    self.uploadS3File(s3, cred, join('player', 'player.css'), rootDir)
                    self.uploadS3Dir(s3, cred, join('player', 'media'))
                except boto3.exceptions.S3UploadFailedError as e:
                    self.writeS3Error(e)
                    return
                except UploadCancelledException as e:
                    self.writeS3Error(e)
                    return

            server.uploadProgress = 100

            uploadsViewInfo = []

            for link in sorted(htmlLinks):
                uploadsViewInfo.append({
                    'title': appInfo['title'],
                    'url' : link,
                    'shorturl' : server.urlBasename(link),
                    'socialText' : 'Check out this interactive web application made with Verge3D!'
                })

            self.write(self.renderTemplate('dialog_published.tpl', {
                'uploadsViewInfo': uploadsViewInfo,
                'licenseInfo': server.getLicenseInfo()
            }))

    class CompressLzmaHandler(tornado.web.RequestHandler, ResponseTemplates):
        async def post(self, tail=None):
            import lzma
            data = self.request.body
            compData = await self.settings['server'].runAsync(lzma.compress, data)
            self.write(compData)

    class SavePuzzlesHandler(tornado.web.RequestHandler):

        def initialize(self, isLibrary, libDelete):
            self.isLibrary = isLibrary
            self.libDelete = libDelete

        def post(self, tail=None):

            server = self.settings['server']

            xmlURL = self.get_argument('xmlURL', strip=False)
            xmlURL = server.resolveURLPath(xmlURL)

            xmlExists = os.path.exists(xmlURL)

            # save backup
            if xmlExists:

                if self.isLibrary:
                    dirname = BACKUP_LIBRARY_DIR
                else:
                    dirname = join(APP_DATA_DIR, BACKUP_PUZZLES_DIR)

                backupDir = join(os.path.dirname(xmlURL), dirname)

                server.backupFile(xmlURL, backupDir)

            # save XML
            xml = self.get_argument('xml', strip=False)
            print('Saving Puzzles XML', xmlURL)
            if self.isLibrary:
                if xmlExists:
                    f = open(xmlURL, 'r', encoding='utf-8', newline='\n')
                    doc = minidom.parse(f)
                    f.close()
                    if self.libDelete:
                        categories = doc.getElementsByTagName('category')
                        for category in categories:
                            if category.hasAttribute('name'):
                                if category.getAttribute('name') == self.get_argument('codeURL', strip=False):
                                    doc.documentElement.removeChild(category)
                    else:
                        xml = minidom.parseString(xml)
                        doc.documentElement.appendChild(xml.documentElement)
                    f = open(xmlURL, 'w', encoding='utf-8', newline='\n')
                    doc.writexml(f)
                    f.close()
                else:
                    f = open(xmlURL, 'w', encoding='utf-8', newline='\n')
                    f.write('<xml>' + xml + '</xml>')
                    f.close()
            else:
                f = open(xmlURL, 'w', encoding='utf-8', newline='\n')
                f.write(xml)
                f.close()

            # save JS
            if not self.isLibrary:
                codeURL = self.get_argument('codeURL', strip=False)
                codeURL = server.resolveURLPath(codeURL)
                code = self.get_argument('code', strip=False)
                print('Saving Puzzles JS', codeURL)
                f = open(codeURL, 'w', encoding='utf-8', newline='\n')
                f.write(code)
                f.close()

            if xmlExists:
                return


    class EnterKeyHandler(tornado.web.RequestHandler, ResponseTemplates):

        def post(self):
            try:
                key = self.get_argument('key')
            except tornado.web.MissingArgumentError:
                self.writeError('Please specify a key.')
                return

            key = key.strip()

            server = self.settings['server']

            if not server.checksum(key) or not server.checkKeyModPackage(key):
                self.writeError('<span class="red">You entered incorrect key. ' +
                        'Please try again or contact the Verge3D support service.</span>')
                return

            licenseInfo = server.getLicenseInfo(key)

            if licenseInfo['type'] == 'OUTDATED':
                self.write(self.renderTemplate('dialog_license_key_done.tpl', {
                    'licenseInfo' : licenseInfo
                }))
                return

            try:
                server.amSettings['licenseKey'] = key
                server.amSettings['licenseKeyVersion'] = licenseInfo['releaseVersion']
                server.saveSettings()
            except PermissionError:
                self.writeError(ACCESS_DENIED_MSG)
                return

            rootDir = server.getRootDir()

            for d in [APPS, 'build']:
                for v3dpath in pathlib.Path(join(rootDir, d)).rglob('v3d*.js'):
                    path = str(v3dpath)
                    server.replaceEngineKey(path, key)

            self.write(self.renderTemplate('dialog_license_key_done.tpl', {
                'licenseInfo' : licenseInfo
            }))

    class UpdateAppInfoHandler(tornado.web.RequestHandler, ResponseTemplates):

        def get(self):
            try:
                app = self.get_argument('app')
            except tornado.web.MissingArgumentError:
                self.writeError('Please specify application')
                self.set_status(400)
                return

            server = self.settings['server']
            appInfo = server.findApp(app)

            if not appInfo or not appInfo['updateInfo']:
                self.writeError('Missing app update information.')
                return

            modules = appInfo['updateInfo']['modules']
            files = appInfo['updateInfo']['files']

            self.write(self.renderTemplate('dialog_update.tpl', {
                'app' : app,
                'modules': [server.pathToUrl(m, quote=False) for m in modules],
                'files': [server.pathToUrl(f, quote=False) for f in files]
            }))

    class UpdateAppHandler(tornado.web.RequestHandler, ResponseTemplates):

        def post(self):
            try:
                app = self.get_argument('app')
            except tornado.web.MissingArgumentError:
                self.writeError('Please specify application filepath')
                self.set_status(400)
                return

            modules = self.get_arguments('module')
            files = self.get_arguments('file')

            if (not len(modules) or modules[0] == '') and (not len(files) or files[0] == ''):
                self.writeError('No files selected for updating.')
                self.set_status(400)
                return

            server = self.settings['server']
            appInfo = server.findApp(app)

            server.updateApp(appInfo, modules, files)

            self.write(self.renderTemplate('dialog_update_done.tpl', {
                'title': appInfo['title']
            }))

    class UpdateAllAppsHandler(tornado.web.RequestHandler, ResponseTemplates):
        def get(self):

            server = self.settings['server']

            for appInfo in server.findApps():
                if appInfo['updateInfo']:
                    self.write('updating {}<br>'.format(appInfo['name']))

                    modules = appInfo['updateInfo']['modules']
                    files = appInfo['updateInfo']['files']

                    server.updateApp(appInfo, modules, files)

    class SettingsHandler(tornado.web.RequestHandler, ResponseTemplates):
        def get(self):
            server = self.settings['server']
            self.write(self.renderTemplate('dialog_settings.tpl', {
                'settings' : server.amSettings
            }))

    class SettingsTemplatesHandler(tornado.web.RequestHandler, ResponseTemplates):
        def get(self):
            server = self.settings['server']
            self.write(self.renderTemplate('dialog_app_templates.tpl', {
                'settings' : server.amSettings
            }))

    class SaveSettingsHandler(tornado.web.RequestHandler, ResponseTemplates):
        def post(self, tail=None):
            settings = json.loads(self.request.body)
            server = self.settings['server']
            server.amSettings.update(settings)
            server.saveSettings()

    class CreateNativeAppHandler(tornado.web.RequestHandler, ResponseTemplates):

        async def receiveElectronBinary(self, targetPlatform):

            binDir = self.settings['server'].getRootDir(True) / 'manager' / 'dist'

            if not binDir.exists():
                binDir.mkdir()

            # increase connection and request timeouts
            # HACK: workaround for SSLCertVerificationError
            client = tornado.httpclient.AsyncHTTPClient(defaults=dict(connect_timeout=60, request_timeout=300, validate_cert=False))

            relResp = await client.fetch(ELECTRON_RELEASE)
            relData = json.loads(relResp.body)

            for asset in relData['assets']:
                if re.match('electron-.+-{}.zip'.format(targetPlatform), asset['name']):
                    # check if already downloaded
                    if not (binDir / asset['name']).exists():
                        print('Fetching Electron binary: {}'.format(asset['name']))

                        distResp = await client.fetch(asset['browser_download_url'])
                        distData = distResp.body

                        with open(binDir / asset['name'], 'wb') as fdist:
                            fdist.write(distData)

                    return binDir / asset['name']

            return None

        async def post(self):
            try:
                app = self.get_argument('app')
                appTemplate = self.get_argument('templateName')
            except tornado.web.MissingArgumentError:
                self.writeError('Please specify app to create template for')
                return

            server = self.settings['server']

            appInfo = server.findApp(app)
            if not appInfo:
                self.writeError('Could not find app: {0}.'.format(app))
                return

            rootDir = server.getRootDir(True)

            zipDir = rootDir / 'zip'

            if not zipDir.exists():
                zipDir.mkdir()

            appDir = appInfo['appDir']
            zipPath = rootDir / 'zip' / (appDir.name + '.zip')

            appName = self.get_argument('appName')
            if not appName:
                self.writeError('Missing app name')
                return

            appID = self.get_argument('appID')
            if not appID:
                self.writeError('Missing app ID')
                return

            appVersion = self.get_argument('appVersion')
            appDescription = self.get_argument('appDescription')
            authorName = self.get_argument('authorName')

            mainHTML = join(appDir, 'index.html')
            if not os.path.exists(mainHTML) and appInfo['html']:
                mainHTML = server.findMainFile(appInfo['name'], appInfo['html'])
            mainHTML = os.path.basename(mainHTML)

            noTrace = lambda *p, **k: None

            with tempfile.TemporaryDirectory() as tmpDir:
                tmpDir = pathlib.Path(tmpDir)

                if appTemplate == 'cordova':
                    print('Creating Cordova app template')

                    server.copyTreeMerge(rootDir / 'manager' / 'templates' / 'Cordova', tmpDir)
                    server.copyTreeMerge(appDir, tmpDir / 'www')

                    server.replaceTemplateStrings(tmpDir / 'config.xml', {
                        'appName': appName,
                        'appDescription': appDescription,
                        'appID': appID,
                        'authorName': authorName,
                        'authorEmail': self.get_argument('authorEmail'),
                        'authorWebsite': self.get_argument('authorWebsite'),
                        'mainHTML': mainHTML
                    })

                    server.replaceTemplateStrings(tmpDir / 'package.json', {
                        'appName': appName,
                        'appVersion': appVersion,
                        'appDescription': appDescription,
                        'appID': appID,
                        'authorName': authorName
                    })

                    # add cordova.js script
                    mainHTMLDest = tmpDir / 'www' / mainHTML
                    if mainHTMLDest.exists():
                        server.replaceTemplateStrings(mainHTMLDest, '</head>',
                                '<script src="cordova.js"></script>\n</head>')

                elif appTemplate == 'electron':
                    print('Creating Electron app template')

                    targetPlatform = self.get_argument('targetPlatform')

                    if targetPlatform != 'none':
                        electronBinary = await self.receiveElectronBinary(targetPlatform)

                        ziptools.extractzipfile(electronBinary, tmpDir, permissions=True, trace=noTrace)

                        if targetPlatform in ['darwin-x64', 'darwin-arm64', 'mas-x64', 'mas-arm64']:

                            macAppName = appID.split('.')[-1] + '.app'

                            os.rename(tmpDir / 'Electron.app', tmpDir / macAppName)

                            plist1 = tmpDir / macAppName / 'Contents' / 'Info.plist'
                            plist2 = (tmpDir / macAppName / 'Contents' / 'Frameworks' /
                                      'Electron Helper.app' / 'Contents' / 'Info.plist')

                            pl = None

                            with open(plist1, 'rb') as fp:
                               pl = plistlib.load(fp)

                            pl['CFBundleDisplayName'] = appName
                            pl['CFBundleIconFile'] = 'verge3d.icns'
                            pl['CFBundleIdentifier'] = appID
                            pl['CFBundleName'] = appID.split('.')[-1]

                            with open(plist1, 'wb') as fp:
                                plistlib.dump(pl, fp)

                            with open(plist2, 'rb') as fp:
                                pl = plistlib.load(fp)

                            pl['CFBundleIdentifier'] = appID + '.helper'
                            pl['CFBundleName'] = appID.split('.')[-1] + ' Helper'

                            with open(plist2, 'wb') as fp:
                                plistlib.dump(pl, fp)

                            # add icons
                            shutil.copy2(rootDir / 'manager' / 'dist' / 'verge3d.icns',
                                         tmpDir / macAppName / 'Contents' / 'Resources')

                            tplDest = tmpDir / macAppName / 'Contents' / 'Resources' / 'app'

                        elif targetPlatform in ['win32-x64', 'win32-ia32', 'win32-arm64']:

                            # replace icon
                            server.runPython([join(BASE_DIR, 'lib', 'peresed.py'),
                                            '-A',
                                            join(BASE_DIR, 'dist', 'verge3d.res'),
                                            join(tmpDir, 'electron.exe')])

                            # replace description
                            server.runPython([join(BASE_DIR, 'lib', 'peresed.py'),
                                            '-V',
                                            'FileDescription={}'.format(appDescription),
                                            join(tmpDir, 'electron.exe')])

                            # replace copyright
                            server.runPython([join(BASE_DIR, 'lib', 'peresed.py'),
                                            '-V',
                                            'LegalCopyright={}'.format(authorName),
                                            join(tmpDir, 'electron.exe')])

                            os.rename(tmpDir / 'electron.exe', tmpDir / (appDir.name + '.exe'))
                            tplDest = tmpDir / 'resources' / 'app'

                        else:

                            os.rename(tmpDir / 'electron', tmpDir / appDir.name)
                            tplDest = tmpDir / 'resources' / 'app'

                    else:
                        tplDest = tmpDir

                    server.copyTreeMerge(rootDir / 'manager' / 'templates' / 'Electron', tplDest)
                    server.copyTreeMerge(appDir, tplDest)

                    server.replaceTemplateStrings(tplDest / 'main.js', {
                        'mainHTML': mainHTML
                    })

                    server.replaceTemplateStrings(tplDest / 'package.json', {
                        'appName': appName,
                        'appVersion': appVersion,
                        'appDescription': appDescription,
                        'authorName': authorName
                    })

                else:
                    self.writeError('Wrong app template: {0}.'.format(appTemplate))
                    return

                print('Packing template ZIP: {}'.format(zipPath))

                await server.runAsync(ziptools.createzipfile, zipPath, [str(p) for p in tmpDir.glob('*')],
                                       zipat=appDir.name, trace=noTrace)


            url = server.pathToUrl(zipPath.relative_to(rootDir), makeAbs=True)

            self.write(self.renderTemplate('dialog_create_native_app_done.tpl', {
                'downloadURL': url
            }))


    class StopServerHandler(tornado.web.RequestHandler, ResponseTemplates):
        def get(self):
            self.settings['server'].stop()
            self.write('ok')

    class RestartServerHandler(tornado.web.RequestHandler, ResponseTemplates):
        def get(self):
            self.settings['server'].stop(True)
            self.write('ok')

    class PuzzlesPluginHandler(tornado.web.RequestHandler, ResponseTemplates):
        def get(self):
            pluginList = []

            server = self.settings['server']
            puzzlesDir = server.getRootDir(True) / PUZZLES_DIR
            pluginsDir = puzzlesDir / PLUGINS_DIR

            if os.path.isdir(pluginsDir):
                for pluginPath in sorted(pathlib.Path(pluginsDir).iterdir()):
                    if pluginPath.is_dir():

                        initFilePath = pluginPath / PUZZLE_PLUGIN_INIT_FILE_NAME
                        if initFilePath.is_file():

                            pluginInfo = {
                                'name': pluginPath.name,
                                'url': str(initFilePath.relative_to(puzzlesDir)),
                                'blocks': {}
                            }

                            for blockPath in sorted(pluginPath.glob('./*.%s' % PUZZLE_PLUGIN_BLOCK_FILE_EXT)):
                                if blockPath.is_file():
                                    pluginInfo['blocks'][blockPath.stem] = {
                                        'url': str(blockPath.relative_to(puzzlesDir))
                                    }

                            pluginList.append(pluginInfo)

            self.finish({ 'pluginList': pluginList })

    class PuzzlesAppListHandler(tornado.web.RequestHandler, ResponseTemplates):
        def get(self):
            appList = []

            server = self.settings['server']

            for appInfo in server.findApps():
                appViewInfo = server.genAppViewInfo(appInfo)
                if appViewInfo['puzzles'] and appViewInfo['puzzles']['logicExists']:
                    appList.append(appViewInfo['puzzles']['url'])

            self.finish({'appList': appList})

    class StaticHandler(tornado.web.StaticFileHandler):
        # disable cache for some resources
        def set_extra_headers(self, path):

            if path.startswith(os.path.join(PUZZLES_DIR, 'media')):
                return

            # https://github.com/e0ne/BlogSamples/blob/master/tornado-nocache/handlers.py
            self.set_header('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0')
            self.set_header('Pragma', 'no-cache')
            self.set_header('Expires', '0')
            now = datetime.datetime.now()
            expiration = now - datetime.timedelta(days=365)
            self.set_header('Last-Modified', expiration)

    def start(self, modPackage):

        print('Starting App Manager server (port {0}, package {1})'.format(str(PORT), modPackage))

        self.modPackage = modPackage
        self.uploadProgress = 0;

        self.loadSettings()
        self.handleUpdate()

        rootDir = self.getRootDir(True)

        # check if user-created puzzles library exists - if not create one
        libXMLPath = rootDir / PUZZLES_DIR / LIBRARY_XML
        if not os.path.exists(libXMLPath):
            try:
                print('Puzzles library file not found, creating one')
                f = open(libXMLPath, 'w', encoding='utf-8', newline='\n')
                f.write('<?xml version="1.0" ?><xml/>')
                f.close()
            except OSError:
                print('Access denied: Puzzles library file was not created')
                pass

        # cleanup temporary zip files
        if os.path.exists(rootDir / 'zip'):
            shutil.rmtree(rootDir / 'zip')

        app = self.createTornadoApp()
        try:
            if not self.asyncioLoop:
                # NOTE: fixes issue with manager running in a thread
                self.asyncioLoop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.asyncioLoop)
            address = '0.0.0.0' if self.amSettings['externalInterface'] else 'localhost'
            tornadoServer = app.listen(PORT, address=address, max_body_size=SERVER_MAX_BODY_SIZE)
        except OSError:
            print('Address already in use, exiting')
            return
        else:
            tornado.ioloop.IOLoop.current().start()

            tornadoServer.stop()
            tornado.ioloop.IOLoop.current().run_sync(tornadoServer.close_all_connections, timeout=5)

            if self.needRestart:
                self.start(modPackage)
                self.needRestart = False

    def stop(self, needRestart=False):

        print('Schedule App Manager server {0}'.format('restart' if needRestart else 'stop'))

        self.needRestart = needRestart

        ioloop = tornado.ioloop.IOLoop.current()
        ioloop.add_callback(ioloop.stop)

    def createTornadoApp(self):
        root = os.path.join(os.path.dirname(__file__), '..')

        handlers = [
            (r'/?$', self.RootHandler),
            (r'/create/?$', self.CreateAppHandler),
            (r'/manage/?$', self.ManageAppHandler),
            (r'/open/?$', self.OpenFileHandler),
            (r'/delete_confirm/?$', self.DeleteConfirmHandler),
            (r'/delete/?$', self.DeleteFileHandler),
            (r'/storage/net/?$', self.ProcessNetworkHandler),
            (r'/storage/lzma/?$', self.CompressLzmaHandler),
            (r'/storage/xml/?$', self.SavePuzzlesHandler, {'isLibrary': False, 'libDelete': False}),
            (r'/storage/xml/library/?$', self.SavePuzzlesHandler, {'isLibrary': True, 'libDelete': False}),
            (r'/storage/xml/libdelete/?$', self.SavePuzzlesHandler, {'isLibrary': True, 'libDelete': True}),
            (r'/enterkey/?$', self.EnterKeyHandler),
            (r'/update_app_info/?$', self.UpdateAppInfoHandler),
            (r'/update_app/?$', self.UpdateAppHandler),
            (r'/update_all_apps/?$', self.UpdateAllAppsHandler),
            (r'/settings/?$', self.SettingsHandler),
            (r'/settings/templates/?$', self.SettingsTemplatesHandler),
            (r'/settings/save?$', self.SaveSettingsHandler),
            (r'/create_native_app/?$', self.CreateNativeAppHandler),
            (r'/stop/?$', self.StopServerHandler),
            (r'/restart/?$', self.RestartServerHandler),
            (r'/puzzles/plugin_list/?$', self.PuzzlesPluginHandler),
            (r'/puzzles/app_list/?$', self.PuzzlesAppListHandler),
            (r'/(.*)$', self.StaticHandler, {'path': root, 'default_filename': 'index.html'}),
        ]

        extAppsDir = self.getExtAppsDir()
        if extAppsDir:
            handlers.insert(-1, (r'/ext/{0}/(.*)$'.format(self.pathToUrl(extAppsDir.name)),
                                 self.StaticHandler,
                                 {'path': str(extAppsDir), 'default_filename': 'index.html'}))

        return tornado.web.Application(handlers, server=self)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1].upper() in ['BLENDER', 'MAX', 'MAYA', 'ALL']:
        modPackage = sys.argv[1].upper()
    else:
        modPackage = 'NONE'

    if len(sys.argv) > 2 and sys.argv[2].upper() == 'RUN_BROWSER':
        import webbrowser
        webbrowser.open('http://localhost:{}/'.format(PORT))

    server = AppManagerServer()
    server.start(modPackage)
