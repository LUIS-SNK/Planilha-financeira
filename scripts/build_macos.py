"""CI macOS: valida o .app; distribui somente após assinatura e notarização."""
import base64
import json
import os
from pathlib import Path
import platform
import secrets
import shlex
import subprocess
import sys
import tempfile

REQUIRED=('MACOS_CERTIFICATE_P12_BASE64','MACOS_CERTIFICATE_PASSWORD',
          'MACOS_SIGNING_IDENTITY','APPLE_ID','APPLE_TEAM_ID','APPLE_APP_PASSWORD')


def run(*args,capture=False):
    # Nunca incluir argumentos na exceção: alguns comandos recebem credenciais.
    result=subprocess.run([str(a) for a in args],text=True,
                          stdout=subprocess.PIPE if capture else None)
    if result.returncode:
        raise RuntimeError(f'Falha em {Path(str(args[0])).name}; código {result.returncode}.')
    return result.stdout if capture else ''


def build(identity=None):
    args=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir',
          '--windowed','--name','MinhasFinancas','--osx-bundle-identifier',
          'com.luissnk.minhasfinancas','--target-arch',platform.machine()]
    if identity: args+=['--codesign-identity',identity]
    run(*args,'app.py')
    run('dist/MinhasFinancas.app/Contents/MacOS/MinhasFinancas','--smoke-test')


def output(signed):
    path=os.environ.get('GITHUB_OUTPUT')
    if path:
        with open(path,'a') as f: f.write(f'signed={str(signed).lower()}\n')
    summary=os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary,'a') as f:
            f.write('## macOS '+platform.machine()+'\n\n')
            f.write('Aplicativo assinado, notarizado e validado pelo Gatekeeper. ZIP disponível nos artefatos.\n' if signed else
                    'Compilação e teste do .app concluídos. **Distribuição bloqueada:** faltam os requisitos Apple Developer. Nenhum aplicativo sem notarização foi publicado. Consulte docs/MACOS.md.\n')


def main():
    if sys.platform!='darwin': raise RuntimeError('Execute este script em um Mac.')
    present=[bool(os.environ.get(name)) for name in REQUIRED]
    if any(present) and not all(present):
        missing=[name for name in REQUIRED if not os.environ.get(name)]
        raise RuntimeError('Configuração Apple incompleta. Requisitos ausentes: '+', '.join(missing))
    if not all(present):
        build(); output(False); return
    identity=os.environ['MACOS_SIGNING_IDENTITY']
    if not identity.startswith('Developer ID Application:'):
        raise RuntimeError('É necessário um certificado Developer ID Application.')
    original_keychains=shlex.split(run('security','list-keychains','-d','user',capture=True))
    with tempfile.TemporaryDirectory() as directory:
        directory=Path(directory); keychain=directory/'signing.keychain-db'
        certificate=directory/'certificate.p12'
        certificate.write_bytes(base64.b64decode(os.environ['MACOS_CERTIFICATE_P12_BASE64'],validate=True))
        certificate.chmod(0o600)
        password=secrets.token_hex(32)
        try:
            run('security','create-keychain','-p',password,keychain)
            run('security','set-keychain-settings','-lut','21600',keychain)
            run('security','unlock-keychain','-p',password,keychain)
            run('security','import',certificate,'-k',keychain,'-P',os.environ['MACOS_CERTIFICATE_PASSWORD'],'-T','/usr/bin/codesign','-T','/usr/bin/security')
            run('security','list-keychains','-d','user','-s',keychain,*original_keychains)
            run('security','set-key-partition-list','-S','apple-tool:,apple:,codesign:','-s','-k',password,keychain)
            build(identity)
            app=Path('dist/MinhasFinancas.app')
            run('codesign','--verify','--deep','--strict','--verbose=2',app)
            submission=directory/'submission.zip'
            run('ditto','-c','-k','--sequesterRsrc','--keepParent',app,submission)
            response=run('xcrun','notarytool','submit',submission,'--apple-id',os.environ['APPLE_ID'],
                         '--team-id',os.environ['APPLE_TEAM_ID'],'--password',os.environ['APPLE_APP_PASSWORD'],
                         '--wait','--output-format','json',capture=True)
            result=json.loads(response)
            if result.get('status')!='Accepted':
                raise RuntimeError('A Apple não aceitou a notarização. Submission ID: '+str(result.get('id','indisponível')))
            run('xcrun','stapler','staple',app)
            run('xcrun','stapler','validate',app)
            run('spctl','--assess','--type','execute','--verbose=2',app)
            release=Path('release'); release.mkdir(exist_ok=True)
            run('ditto','-c','-k','--sequesterRsrc','--keepParent',app,release/f'MinhasFinancas-macOS-{platform.machine()}.zip')
            output(True)
        finally:
            # O keychain temporário não deve permanecer no runner após falhas.
            try: run('security','list-keychains','-d','user','-s',*original_keychains)
            finally:
                if keychain.exists(): run('security','delete-keychain',keychain)

if __name__=='__main__':
    try: main()
    except Exception as error:
        # Mensagens controladas, sem traceback com argumentos de subprocessos.
        print(str(error),file=sys.stderr)
        sys.exit(1)
