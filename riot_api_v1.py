import requests
import json
import sys, os
import datetime
import random
import time
import glob
import math

with open('apikey.txt') as file:
	dev_api_key = file.read()
	#print(dev_api_key, type(dev_api_key))

summonername = 'vinchileo'

FILE_ACCOUNTS = 'accounts.txt'
DIR_MATCHLISTS = 'matchlists'
DIR_MATCHES = 'matches'
FILE_CHAMPIONS = 'champions.json'
CHAMPIONS_WIN = 'champions_win.json'
CHAMPIONS_FAIL= 'champions_fail.json'
CHAMPIONS_RATIO='champions_ratio.json'
accounts = [] #accounds taked by summonername
lastheader = {}
queue_names = {'420':'5v5 Ranked Solo games', '1200':'Nexus Blitz games'}
matchlabels = ['matchid','queue','win','p1','p2','p3','p4','p5','p6','p7','p8','p9','p10','c1','c2','c3','c4','c5','c6','c7','c8','c9','c10','creation','duration'] 
#win - 100(Blue), 200(Red)
#p1-10 - accountid
#c1-c10 - champions
matches = [] #from matchlists
cashedmatches = [] #from matches
FILE_CASHEDMATCHES = 'cashedmatches.txt'
players = {} #set accountids from cashedmatches
FILE_PLAYERS = 'players.txt'
champoins_set = {}
champions_notfound = {
	141:'Kayn',
	555:'Pyke',
	142:'Zoe',
	497:'Rakan',
	145:'Kaisa',
	498:'Xayah',
	516:'Ornn',
}



'''
get account id:
https://ru.api.riotgames.com/lol/summoner/v3/summoners/by-name/vinchileo?api_key=RGAPI-94253b8f-866b-47a9-a7ac-1e9869022758
{"id":308311,"accountId":200220472,"name":"vinchileo","profileIconId":3552,"revisionDate":1534214164000,"summonerLevel":139}
'X-App-Rate-Limit': '20:1,100:120', 'X-App-Rate-Limit-Count': '1:1,1:120', 
'X-Method-Rate-Limit': '600:60', 'X-Method-Rate-Limit-Count': '1:60'

matchlist with matchid from accountid, last 100:
https://ru.api.riotgames.com/lol/match/v3/matchlists/by-account/200220472?queue=420&season=11&api_key=RGAPI-94253b8f-866b-47a9-a7ac-1e9869022758
'X-App-Rate-Limit': '20:1,100:120', 'X-App-Rate-Limit-Count': '1:1,3:120', 
'X-Method-Rate-Limit': '1000:10', 'X-Method-Rate-Limit-Count': '1:10'

match stats from matchid:
https://ru.api.riotgames.com/lol/match/v3/matches/182423193?api_key=RGAPI-94253b8f-866b-47a9-a7ac-1e9869022758
'X-App-Rate-Limit': '20:1,100:120', 'X-App-Rate-Limit-Count': '1:1,2:120',
'X-Method-Rate-Limit': '500:10', 'X-Method-Rate-Limit-Count': '1:10'

ok 1. load cashed file: accounts.txt (name, id and others)
ok 2. get account id - 1)from file, if not - 2)from api
ok 3. save data to file
ok getstats() - write last header stats (rate limits)
ok get matches by accountid - нужно придумать порядок обхода и способ хранения.
ok getstats() - cashed static data for champions
need:

accountid() - if cashed data more 1 day -  update account (в зависимости от частоты игр)

accounts - add currentplatformid
getlastmatches() - check update time and clear cash more 100*matchdurtion(15 min)=1day
getstats() - get all matches and compare with cashed (for all queue, 1200 - ok)
modify paths in functions(?) for more queue 
!!! getnewmatch()[1200]->getlastmatches(id,queue) - add queue parameters
getstats() - top champions - WIN-FAIL-WIN/FAIL-MOSTPLAYED, подумать как построить классификатор и подготовить данные
ML - predict win chance by 5 champions draft
cashedmatches - добавить поле version
!!! button 'refresh stats'  - only 1 time per hours, cash result in file (load_chashed_matches() check file with cash)
page 'load matches for summoner'


'''
def loadaccounts():
	global accounts

	try:
		file = open(FILE_ACCOUNTS, 'r')
		accounts = json.load(file)
		file.close()
		print('accounts loaded from file')
	except Exception as error:
		print('file accounts not found, we need create file')
		saveaccounts()

def saveaccounts():
	file = open(FILE_ACCOUNTS, 'w', encoding='utf8')
	json.dump(accounts, file)
	file.close()
	print('saved in file {} accounts count: {}'.format(FILE_ACCOUNTS, len(accounts)))

#get accountid by summoner name
def accountid(name):
	global accounts, lastheader

	if len(accounts)==0:
		loadaccounts()

	cashed = False
	print('we have {} accounts in cash db'.format(len(accounts)))
	for id in accounts:
		if id['name']==name:
			print('we find name in cash')
			print(id)
			cashed = True
			return id['accountId']
	if not cashed:
		print('need find from api')
		url = 'https://ru.api.riotgames.com/lol/summoner/v3/summoners/by-name/'+name+'?api_key='+dev_api_key
		response = requests.get(url)
		id = response.json()
		lastheader = response.headers
		print('result:\n',id)
		#{'status': {'message': 'Data not found', 'status_code': 404}}
		#{'id': 6342903, 'accountId': 202721890, 'name': 'dsfsdfdsf', 'profileIconId': 28, 'revisionDate': 1495758262000, 'summonerLevel': 1}
		if 'status' in id.keys():
			print('summoner name not found from api')
			return None
		else:
			accounts.append(id)
			saveaccounts()
			return id['accountId']

#print matchlist in getlastmatches
def printmatchlist(matchlist):
	print('result:\n')
	print('total games: {}'.format(matchlist['totalGames']))
	print('listed games: {}'.format(len(matchlist['matches'])))
	#for check cashed matches:
	m2 = [match[0] for match in cashedmatches]

	for match in matchlist['matches']:
		time = match['timestamp']/1000
		timestring = datetime.datetime.fromtimestamp(time)#.strftime('%Y-%m-%d %H:%M:%S')
		string = 'time: {} gameid: {} lane: {} role: {} queue: {} champion: {}'
		if int(match['gameId']) in m2:
			string+=' [CASHED]'
		print(string.format(
			timestring,match['gameId'],match['lane'],match['role'],match['queue'],match['champion']))

#in menu and getnewmatch()
def getlastmatches(accountid, queue='420', season='11'):
	global lastheader
	cashed = False

	#dir:matchlists/file:accountid_queue_season[_beginIndex].txt
	if not os.path.exists(DIR_MATCHLISTS):
		os.makedirs(DIR_MATCHLISTS)
	filename = accountid+'_'+queue+'_'+season+'.txt'
	if os.path.isfile(DIR_MATCHLISTS+'/'+filename):
		#check time of file:
		modify_time = os.path.getmtime(DIR_MATCHLISTS+'/'+filename)
		current_time = datetime.datetime.now().timestamp()
		print('modify time fo cashed file: ',modify_time, ' current:',current_time)
		diff = (current_time-modify_time)
		print(' diff:', diff, ' days>:',diff//86400)
		if diff<86400:
			#get matchlist from cashed file:
			print('matchlist cashed in file: '+filename)
			file = open(DIR_MATCHLISTS+'/'+filename, 'r')
			matchlist = json.load(file)
			file.close()
			printmatchlist(matchlist)
			cashed = True
		else:
			#refresh cashed file > 1 day
			print('cashed file ',filename,' too old, need refresh matchlist')
	
	if not cashed:
		print('need find from api ( '+queue_names[queue]+' , season 2018)')
		url = 'https://ru.api.riotgames.com/lol/match/v3/matchlists/by-account/'+accountid+'?queue='+queue+'&season='+season+'&api_key='+dev_api_key
		response = requests.get(url)
		matchlist = response.json()
		lastheader = response.headers
		if 'status' in matchlist.keys():
			print('accountid not found from api or no games')
			return []
		else:
			#print info from matchlist:
			printmatchlist(matchlist)
			#save matchlist:
			file = open(DIR_MATCHLISTS+'/'+filename, 'w', encoding='utf8')
			json.dump(matchlist, file)
			file.close()
			print('matchlist saved in file: '+filename)
			#account matches stats:
	#matchlist return:
	return matchlist['matches']

def printmatch(match):
	print('creation time: ',datetime.datetime.fromtimestamp(match['gameCreation']/1000))
	print('duration time: {} min {} sec'.format(match['gameDuration']//60, match['gameDuration']%60))
	teams = match['teams']
	win = sorted(teams, key=lambda k: k['teamId'])
	for team in teams:
		print('id: ',team['teamId'],'win: ',team['win'])
	if win[0]['win']=='Win':
		print('win: Blue')
	else:
		print('win: Red')
	participants = match['participants']
	for player in participants:
		print('player:{} team:{} champion:{} tier:{}'.
			format(player['participantId'],player['teamId'],player['championId'],player['highestAchievedSeasonTier']))
	players = match['participantIdentities']
	for player in players:
		part = player['participantId']
		pl = player['player']
		try:
			print('player:{} name:{} accountid:{}'.format(part,pl['summonerName'],pl['currentAccountId']))
		except:
			print('player:{} name:{} accountid:{}'.format(part,'wrong format',pl['currentAccountId']))


def getmatch(matchid):
	global lastheader, players
	cashed = False

	#dir:matches/file:matchid.txt
	if not os.path.exists(DIR_MATCHES):
		os.makedirs(DIR_MATCHES)
	filename = matchid + '.txt'
	if os.path.isfile(DIR_MATCHES+'/'+filename):
		print('match cashed in file: '+filename)
		file = open(DIR_MATCHES+'/'+filename, 'r')
		match = json.load(file)
		file.close()
		printmatch(match)
		cashed = True

	if not cashed:
		print('need find from api')
		url = 'https://ru.api.riotgames.com/lol/match/v3/matches/'+matchid+'?api_key='+dev_api_key
		response = requests.get(url)
		match = response.json()
		lastheader = response.headers
		if 'status' in match.keys():
			print('match not found from api')
			return match
		else:
			printmatch(match)
			file = open(DIR_MATCHES+'/'+filename, 'w', encoding='utf8')
			json.dump(match, file)
			file.close()
			print('match saved in file: '+filename)
			#update cashedmatches
			cashedmatch = update_cashed_matches(match)
			#update players
			before = len(players)
			players = players.union(set(cashedmatch[3:3+10]))
			print('players before:{} after:{}'.format(before, len(players)))
			print('cashedmatches updated: {} matches'.format(len(cashedmatches)) )
	return match


def getplayersfrommatch(matchid):
	match = getmatch(matchid)
	matchplayers = [i['player']['accountId']for i in match['participantIdentities']]
	print(matchplayers)
	return matchplayers

def load_players_cashedmatches():
	allplayers = set()
	for item in cashedmatches:
		matchplayers = set(item[3:3+10])
		#print(len(matchplayers), matchplayers)
		allplayers = allplayers.union(matchplayers)
	print('all players in cashedmatches:',len(allplayers))
	return allplayers


def getstats():
	if len(accounts)==0:
		loadaccounts()
	acc_count = len(accounts)
	print('accounts:', acc_count)
	print('top 20 cashed accounts sorted by revisionDate:')
	top = sorted(accounts, key=lambda k: k['revisionDate'], reverse=True)[:20] 
	for id in top:
		time = id['revisionDate']/1000
		timestring = datetime.datetime.fromtimestamp(time)#.strftime('%Y-%m-%d %H:%M:%S')
		print('time: {} name:{} accountid:{} level: {}'.format(timestring,id['name'],id['accountId'],id['summonerLevel']))
	print('last headers:\n', lastheader)
	
	print(queue_names['1200'],':')
	matchesinlists = matchlists_stats('1200')
	cashed = set([match[0] for match in cashedmatches])
	noncashed = matchesinlists.difference(cashed)
	print('all cashed matches:{} all players in cashed:{} matches in 2nb lists:{} matches 2nb non cashed:{}'
		.format(len(cashedmatches),len(players),len(matchesinlists),len(noncashed)))
	print('result %:',len(cashedmatches)/len(matchesinlists)*100)

	#save cashes to files:
	savecash()

	#pandas:
	import numpy as np
	import pandas as pd
	import collections
	
	#win
	test_win = [i[13:13+5] if i[2]==100 else i[13+5:13+10] for i in cashedmatches ]
	test2 = [item for sublist in test_win for item in sublist]
	champion_counter_win=collections.Counter(test2)
	#fail
	test_fail = [i[13:13+5] if i[2]==200 else i[13+5:13+10] for i in cashedmatches ]
	test2 = [item for sublist in test_fail for item in sublist]
	champion_counter_fail=collections.Counter(test2)

	#print(champion_counter)
	#static champions:
	#https://ru.api.riotgames.com/lol/static-data/v3/champions?locale=en_US&dataById=false&api_key=RGAPI-71b99518-edd0-4440-9ea3-a137c15ab056
	#url = 'https://ru.api.riotgames.com/lol/static-data/v3/champions?locale=en_US&dataById=false&api_key='+dev_api_key
	try:
		file = open(FILE_CHAMPIONS, 'r')
		data = json.load(file)
		file.close()
		print('champions loaded from file')
	except Exception as error:
		print('file champions not found, we need create file')
		url = 'https://ru.api.riotgames.com/lol/static-data/v3/champions?locale=en_US&dataById=false&api_key='+dev_api_key
		#new:
		#http://ddragon.leagueoflegends.com/cdn/8.16.1/data/en_US/championFull.json
		response = requests.get(url)
		data = response.json()
		file = open(FILE_CHAMPIONS, 'w', encoding='utf8')
		json.dump(data, file)
		file.close()
		print('saved in file {}'.format(FILE_CHAMPIONS))

	champions = {value['id']:value['key'] for value in data['data'].values()}
	print('champions:',len(champions))

	print('counters win: ',len(dict(champion_counter_win)))
	print('counters fail:',len(dict(champion_counter_fail)))
	
	champions_win = {}
	for k,v in dict(champion_counter_win).items():
		try:
			champions_win[champions[k]]=v
		except Exception as error:
			champions_win[champions_notfound[k]]=v
			print('not found:',k,v)
	#sorted_win_champs = [(k,v) for k,v in champions_win.items()]
	sorted_win_champs = sorted(champions_win.items(), key=lambda x: x[1], reverse=True)
	print(sorted_win_champs)

	champions_fail = {}
	for k,v in dict(champion_counter_fail).items():
		try:
			champions_fail[champions[k]]=v
		except Exception as error:
			champions_fail[champions_notfound[k]]=v
			print('not found:',k,v)
	#sorted_win_champs = [(k,v) for k,v in champions_win.items()]
	sorted_fail_champs = sorted(champions_fail.items(), key=lambda x: x[1], reverse=True)
	print(sorted_fail_champs)

	#win/fail
	champions_ratio = {}
	for k,v in champions_win.items():
		champions_ratio[k]=math.floor(v/champions_fail[k]*100)/100
	#print(champions_ratio)
	sorted_ratio_champs = sorted(champions_ratio.items(),key=lambda x: x[1], reverse=True )
	print(sorted_ratio_champs)

	#export results:
	file = open(CHAMPIONS_WIN, 'w', encoding='utf8')
	json.dump(champions_win, file)
	file.close()
	file = open(CHAMPIONS_FAIL, 'w', encoding='utf8')
	json.dump(champions_fail, file)
	file.close()
	file = open(CHAMPIONS_RATIO, 'w', encoding='utf8')
	json.dump(champions_ratio, file)
	file.close()
	
	

	'''
	#analysis:
	df = pd.DataFrame(cashedmatches)
	print(df.head(10))
	df_test = pd.DataFrame(test)
	print(df_test.head(10))
	'''
def print_champions_winfail():
	file = open(CHAMPIONS_WIN, 'r')
	champions_win = json.load(file)
	file.close()
	file = open(CHAMPIONS_FAIL, 'r')
	champions_fail = json.load(file)
	file.close()
	sorted_win_champs = sorted(champions_win.items(), key=lambda x: x[1], reverse=True)
	sorted_fail_champs = sorted(champions_fail.items(), key=lambda x: x[1], reverse=True)
	for item in sorted_win_champs:
		print(item, item[0], item[1])
	for item in sorted_fail_champs:
		print(item, item[0], item[1])

		
#cashedmatches = [] #from cashed matches (id, stats)
def load_cashed_matches():
	#import glob
	if os.name=='nt':
		cashedids = [item.split('\\')[1].split('.')[0] for item in glob.glob(DIR_MATCHES+'\*.txt')]
	else:
		cashedids = [item.split('/')[1].split('.')[0] for item in glob.glob(DIR_MATCHES+'/*.txt')]
	print('cashed matches ids:')
	for id in cashedids:
		#print('match:',id)
		file = open(DIR_MATCHES+'/'+id+'.txt', 'r')
		match = json.load(file)
		file.close()
		#printmatch(match)
		update_cashed_matches(match)


#in getmatch and load_cashed_matches
def update_cashed_matches(match):
	global cashedmatches
	#['matchid','queue','win','p1-10','c1-10','creation','duration']
	matchstat = [match['gameId'], match['queueId']]
	teams = match['teams']
	if teams[0]['win']=='Win':
		matchstat.append(100)
	else:
		matchstat.append(200)
	for player in match['participantIdentities']:
		matchstat.append(player['player']['currentAccountId'])
	for player in match['participants']:
		matchstat.append(player['championId'])
	matchstat.append(match['gameCreation'])
	matchstat.append(match['gameDuration'])
	cashedmatches.append(matchstat)
	return matchstat

#in getmanymatches(count)
def getnewmatch():
	players_count = len(players)
	print('players before:',players_count)
	id = random.sample(players,1)[0]
	print('selected player accountid:', id)
	#get 2nb matchlist for player and find max noncashed matchid
	m1 = [match['gameId'] for match in getlastmatches(str(id), '1200')]
	m2 = [match[0] for match in cashedmatches]
	#print(m1)
	#print(m2)
	noncashed = [i for i in m1 if i not in m2]
	if noncashed == []:
		print('all matches for player cashed')
		return False
	selected = max(noncashed)
	print('selected matchid:',selected)
	#get non cashed match
	match = getmatch(str(selected))

	if lastheader != {}:
		try:
			print('api count:',lastheader['X-App-Rate-Limit-Count'])
		except Exception as error:
			print('error of print rate count in getnewmatch:', error)
	return True

def getmanymatches(count):
	for i in range(int(count)):
		old_stdout = sys.stdout
		sys.stdout = open(os.devnull, "w")
		resultflag = getnewmatch()
		sys.stdout = old_stdout
		if lastheader != {}:
			try:
				appcount = lastheader['X-App-Rate-Limit-Count']
			except Exception as error:
				appcount = 'error in appcount'
				print(error)
		print('players:{} matches:{} appcount: {}, flag: {}'.format(len(players),len(cashedmatches),appcount, resultflag))
		if resultflag:
			time.sleep(3)

def matchlists_stats(queue):
	if os.name=='nt':
		matchlists = [item.split('\\')[1] for item in glob.glob(DIR_MATCHLISTS+'\*.txt') if '_'+queue+'_' in item]
	else:
		matchlists = [item.split('/')[1] for item in glob.glob(DIR_MATCHLISTS+'/*.txt') if '_'+queue+'_' in item]

	#matchlists = [item.split('\\')[1] for item in glob.glob(DIR_MATCHLISTS+'\*.txt') if '_'+queue+'_' in item]
	print('cashed matchlists:')
	m2=set()
	for name in matchlists:
		#print('match:',id)
		if queue == name.split('_')[1]:
			file = open(DIR_MATCHLISTS+'/'+name, 'r')
			matchlist = json.load(file)
			file.close()
			m1 = set([item['gameId'] for item in matchlist['matches']])
			m2=m2.union(m1)
			#print('games:{} len:{} allgames:{}'.format(matchlist['totalGames'],len(m1),len(m2)))
	return m2
			
def savecash():
	#players, cashedmatches
	file = open(FILE_CASHEDMATCHES, 'w', encoding='utf8')
	json.dump(cashedmatches, file)
	file.close()
	file = open(FILE_PLAYERS, 'w', encoding='utf8')
	json.dump(list(players), file)
	file.close()
	print('cash saved in files: {} {}'.format(FILE_CASHEDMATCHES, FILE_PLAYERS))

def initcash(fromfile=False):
	global players, cashedmatches
	if not fromfile:
		#load matches from cash
		print('calculate cash from cashed matches')
		load_cashed_matches()
		print(len(cashedmatches))
		#for i in cashedmatches:
		#	print(i)
		#load players id from cashedmatches
		players=load_players_cashedmatches()
	else:
		#load matches and players from file
		print('load cash from files')
		file = open(FILE_CASHEDMATCHES, 'r')
		cashedmatches=json.load(file)
		file.close()
		print('all cashed matches',len(cashedmatches))
		file = open(FILE_PLAYERS, 'r')
		players=set(json.load(file))
		file.close()
		print('all players in cashedmatches:',len(players))


#-------------MENU----------------------

def main_menu():
	global players
	initcash()
	'''
	#load matches from cash
	load_cashed_matches()
	print(len(cashedmatches))
	#for i in cashedmatches:
	#	print(i)
	#load players id from cashedmatches
	players=load_players_cashedmatches()
	'''

	menu = {}
	menu['0']="get stats"
	menu['1']="get accountid by name" #ok
	menu['2rs']="get ranked solo matches by accountid"#ok
	menu['2nb']="get nexus blitz matches by accountid"#ok
	menu['3']="get match by matchid"#ok
	menu['4']="get match timeline by matchid" #later
	menu['5']="print champions win/fail stats"#!!!
	menu['6']="get accountid from match by matchid"#ok
	menu['7']="get random player, matchlist 2nb, download latest non cashed match 2nb"#ok
	menu['8']="get many matches 2nb (like 7)"#ok
	menu['9']="get matchlists from files 2nb and calculate all matches"#ok
	menu['10']="save cash in files"#!!!
	menu['q']="Exit"
	#OK 1. get matches from cash from start (and update after getmatch)
	#OK 2. get players from cashedmatches 
	#matches = [] #from matchlists (id, cashed[True/False], timestamp)
	#OK cashedmatches = [] #from cashed matches (id, stats)
	#accounts = [] #from accounts.txt
	#OK players = set{} #from cashedmatches (id)
	while True: 
		options=menu.keys()
		print('\n')
		for entry in options: 
			print (entry, menu[entry])
		selection=input("Please Select:\n") 
		if selection =='0': 
			getstats()
		elif selection == '1': 
			input_name = input('write summoner name here (RU server):\n')
			print('id: {}'.format(accountid(input_name)))
		elif selection == '2rs':
			input_id = input('write account id here (RU server):\n')
			matches = getlastmatches(input_id)
		elif selection == '2nb':
			input_id = input('write account id here (RU server):\n')
			matches = getlastmatches(input_id, '1200')
			#print(matches)
		elif selection == '3':
			matchid = input('write match id here (RU server):\n')
			match = getmatch(matchid)
		elif selection == '4': 
			pass
		elif selection == '5': 
			print_champions_winfail()
		elif selection == '6':
			matchid = input('write match id here (RU server):\n')
			matchplayers = getplayersfrommatch(matchid) #list of match currentAccountId
		elif selection == '7': 
			resultflag = getnewmatch()
		elif selection == '8':
			input_id = input('write count of new matches (RU server):\n')
			getmanymatches(input_id)
		elif selection == '9':
			matchesinlists = matchlists_stats('1200')
			print(len(matchesinlists))
		elif selection == '10':
			savecash()
		elif selection == 'q': 
			break
		else: 
			print("Unknown Option Selected!")


# Main Program
if __name__ == "__main__":
	# Launch main menu
	main_menu()