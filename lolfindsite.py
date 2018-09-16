#init cash
import riot_api_v1 as riot
riot.initcash(fromfile=True)
#init libs
import datetime
import json


from flask import Flask
from flask import render_template
from flask import abort, redirect, url_for
app = Flask(__name__)

#url_for('static', filename='lol.png')

@app.route('/')
def hello_world():
	q1 = riot.queue_names['1200']
	s1 = 'cash statistics about '+q1
	s2 = 'champions ordered by the number of Winned and Failed matches'
	return render_template("index.html",title = 'LOLFIND.RU', s1 = s1, s2 = s2)

@app.route('/stats/')
def viewstats():
	s1 = riot.queue_names['1200'] #nexus blitz queue name
	matchesinlists = riot.matchlists_stats('1200') #load files in matchlists folder
	cashed = set([match[0] for match in riot.cashedmatches])
	noncashed = matchesinlists.difference(cashed)
	s2 = 'all cashed matches:{} all players in cashed:{} matches in 2nb lists:{} matches 2nb non cashed:{}'.format(len(riot.cashedmatches),len(riot.players),len(matchesinlists),len(noncashed))
	s3 = 'result %:'+str(len(riot.cashedmatches)/len(matchesinlists)*100)

	s4 = '<form method="get" action="/stats_refresh/"><button type="submit">Refresh cash stats</button></form>'

	result = s1 + '<p>' + s2 + '<p>' + s3 + '<p>' + s4
	return result

@app.route('/summoner/<string:name>')
def show_matches(name):
	id = riot.accountid(name) #request api of cash for accountid
	if id is None:
		return 'Summoner name {} not found on RU server'.format(name)
	s1 = 'Summoner name: {} account id:{}'.format(name, id)
	matchlist = riot.getlastmatches(str(id), '1200')

	cashed = [match[0] for match in riot.cashedmatches]

	s2 = '<p>'
	for match in matchlist:
		time = match['timestamp']/1000
		timestring = datetime.datetime.fromtimestamp(time)#.strftime('%Y-%m-%d %H:%M:%S')
		string = 'time: {} gameid: {} lane: {} role: {} queue: {} champion: {}'
		if int(match['gameId']) in cashed:
			string+=' [CASHED]'
		s3 = string.format(timestring,match['gameId'],match['lane'],match['role'],match['queue'],match['champion'])
		s2  = s2 + s3 + '<p>'
	return s1+s2

@app.route('/stats_refresh/')
def refreshstats():
	riot.cashedmatches = [] #from matches
	riot.players = {} #set accountids from cashedmatches
	riot.initcash(fromfile=True)
	return redirect(url_for('viewstats'))

@app.route('/champions_win_fail/')
def champions_win_fail():
	file = open(riot.CHAMPIONS_WIN, 'r')
	champions_win = json.load(file)
	file.close()
	file = open(riot.CHAMPIONS_FAIL, 'r')
	champions_fail = json.load(file)
	file.close()
	file = open(riot.CHAMPIONS_RATIO, 'r')
	champions_ratio = json.load(file)
	file.close()
	sorted_win_champs = sorted(champions_win.items(), key=lambda x: x[1], reverse=True)
	sorted_fail_champs = sorted(champions_fail.items(), key=lambda x: x[1], reverse=True)
	sorted_ratio_champs = sorted(champions_ratio.items(), key=lambda x: x[1], reverse=True)
	
	s0 = '<h1> Total cashed games: '+str(len(riot.cashedmatches))+'</h1>'
	s1 = '<h2> WINS </h2>'
	s2 = '<h2> FAILS </h2>'
	s3 = '<h2> WIN/FAIL </h2>'
	
	s4 = '<table style="width: 10px; height: 10px; margin-left: auto; margin-right: auto;" border="1" cellspacing="1" cellpadding="1"><thead><tr>'
	s4+= '<th>Champion</th><th>Wins</th></tr></thead>'
	s4+= '<tbody>'
	for item in sorted_win_champs:
		s4+='<tr><td>'+item[0]+'</td><td>'+str(item[1])+'</td></tr>'
	s4+='</tbody></table>'

	s5 = '<table style="width: 10px; height: 10px; margin-left: auto; margin-right: auto;" border="1" cellspacing="1" cellpadding="1"><thead><tr>'
	s5+= '<th>Champion</th><th>Fails</th></tr></thead>'
	s5+= '<tbody>'
	for item in sorted_fail_champs:
		s5+='<tr><td>'+item[0]+'</td><td>'+str(item[1])+'</td></tr>'
	s5+='</tbody></table>'

	s6 = '<table style="width: 10px; height: 10px; margin-left: auto; margin-right: auto;" border="1" cellspacing="1" cellpadding="1"><thead><tr>'
	s6+= '<th>Champion</th><th>Win/Fails</th></tr></thead>'
	s6+= '<tbody>'
	for item in sorted_ratio_champs:
		s6+='<tr><td>'+item[0]+'</td><td>'+str(item[1])+'</td></tr>'
	s6+='</tbody></table>'

	r = s0
	r+= '<table><thead><tr><th>'+s1+'</th><th>'+s2+'</th><th>'+s3+'</th></tr></thead>'
	r+= '<tbody><tr><td>'+s4+'</td><td>'+s5+'</td><td>'+s6+'</td></tr></tbody></table>'
	return r
