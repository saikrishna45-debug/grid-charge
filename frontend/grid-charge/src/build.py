import os,re
d=os.path.dirname(os.path.abspath(__file__)); out=os.path.dirname(d)
rd=lambda n:open(os.path.join(d,n),encoding='utf-8').read()
css=rd('styles.css')+chr(10)+rd('theme.css'); body=rd('body.html')
import_mark=''
js='\n'.join(rd(n) for n in ['data.js','api.js','charts.js','hero.js','pages.js','app.js'])
body=body.replace('<!--MARK-->','<svg class="brand-mark" viewBox="0 0 34 34" aria-hidden="true"><circle cx="17" cy="17" r="13" fill="none" stroke="currentColor" stroke-width="3.4" stroke-dasharray="64 18" stroke-linecap="round" transform="rotate(-72 17 17)"/><path d="M18.6 7.5 11 18.6h5.2L15.2 26.5 23 15.3h-5.2z" fill="#f5b041"/></svg>')
fonts='<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;600&family=Manrope:wght@400;500;600;700;800&family=Merriweather:ital,wght@0,700;0,900;1,400&display=swap">'
frag=f'<title>Grid Charge</title>\n{fonts}\n<style>\n{css}\n</style>\n{body}\n<script>\n{js}\n</script>\n'
open(os.path.join(out,'publish.html'),'w',encoding='utf-8').write(frag)
full=f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><style>[hidden]{{display:none!important}}html,body{{margin:0}}</style></head><body>\n{frag}</body></html>\n'
open(os.path.join(out,'GridCharge.html'),'w',encoding='utf-8').write(full)
print('built',len(full)//1024,'KB')
