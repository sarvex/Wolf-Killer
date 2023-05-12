# -*- coding:utf-8 -*-
from  __future__ import unicode_literals
from flask import Flask, render_template, session, request, redirect, url_for, flash, jsonify
from flask_script import Manager
from flask_bootstrap import Bootstrap
from flask_wtf import Form
from wtforms import StringField, IntegerField, BooleanField, SubmitField, RadioField
from wtforms.validators import Required

from game import *

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hard to guess string'

manager = Manager(app)
bootstrap = Bootstrap(app)

game = Game()
pdb = PlayerDatabase()

class LoginForm(Form):
    username = StringField('用户名', validators=[Required()])
    password = StringField('密码', validators=[Required()])

    submit = SubmitField('登录')

class GameConfigForm(Form):
    wolfCnt = IntegerField('狼人数量', validators=[Required()])
    vilCnt  = IntegerField('村民数量',  validators=[Required()])
    witchEn = BooleanField('女巫')
    guardEn = BooleanField('守卫')
    hunterEn = BooleanField('猎人')
    proEn = BooleanField('预言家')
    metric = RadioField('选择胜利方式', choices=[('side', '屠边'),
        ('all', '屠城')], default='side', validators = [Required()])

    submit = SubmitField('新建游戏')

class JoinForm(Form):
    submit = SubmitField('加入游戏')

#
# REDIRECT FOR ALL ENTRY
#
def redirectAll(session, now):
    global game
    if (not pdb.exist(session.get('name'))):
        goto = 'index'
    else:
        pl = pdb.players[session['name']]
        if (game.state == game.GST_ROOM_CLOSED):
            game = Game()
        goto = 'room_play' if (game.checkPlayer(pl.username)) else 'lobby'
    return None if goto == now else goto

#
# API for Host
#
@app.route('/api/host/start_game', methods=['POST'])
def api_host_start_game():
    if (not game.checkHost(session['name'])):
        return ""

    if (game.state != Game.GST_WAIT_JOIN):
        return jsonify({ 'msg':  "wrong game state" })

    game.start()
    return jsonify({ 'msg':  "success" })

@app.route('/api/host/close_room', methods=['POST'])
def api_host_close_room():
    if (not game.checkHost(session['name'])):
        return ""
    game.close()
    return redirect(url_for("index"))

#
# API in Game
#
@app.route('/api/get_message', methods=['GET'])
def api_get_message():
    msg = game.deliver.fetch(session['name'])
    print(session['name'], " get message ", msg)
    return jsonify({'messages': msg})

@app.route('/api/send_message', methods=['POST'])
def api_send_message():
    print ('send message', request.values.get('type'))
    game.doStage(session['name'], request.values)
    return jsonify({'messages': 'success'})

@app.route('/api/enter_room', methods=['GET', 'POST'])
def api_enter_romm():
    name = session['name']
    game.enterRoom(name)
    return "hello"

@app.route('/api/quit_room', methods=['GET', 'POST'])
def api_quit_room():
    name = session['name']
    game.quitRoom(name)
    return "bye"

@app.route('/admin/reset', methods=['GET', 'POST'])
def api_force_close():
    global game, pdb
    game = Game()
    pdb = PlayerDatabase()
    return "you are admin"

#
# GAME ROOM
#
@app.route('/room', methods=['GET', 'POST'])
def room_play():
    if goto := redirectAll(session, 'room_play'):
        return redirect(url_for(goto))

    return render_template('play.html')

@app.route('/lobby', methods=['GET', 'POST'])
def lobby():
    global game
    if goto := redirectAll(session, 'lobby'):
        return redirect(url_for(goto))

    cfgForm  = GameConfigForm()
    joinForm = JoinForm()
    name = session['name']
    pl = pdb.players[name]

    if game.state == Game.GST_NEWGAME:
        if cfgForm.validate_on_submit():
            game = Game()
            game.setConfig(GameConfig(wolfCnt = cfgForm.wolfCnt.data,
              vilCnt = cfgForm.vilCnt.data, guardEn = cfgForm.guardEn.data,
              witchEn = cfgForm.witchEn.data, hunterEn = cfgForm.hunterEn.data,
              proEn = cfgForm.proEn.data, metric = cfgForm.metric.data))
            print("win metric", cfgForm.metric.data)
            game.state = Game.GST_WAIT_JOIN
            game.setHost(pl)
            return redirect(url_for('room_play'))
        return render_template('lobby.html', form = cfgForm, name = name)
    elif game.state == Game.GST_WAIT_JOIN:
        if joinForm.validate_on_submit():
            if game.addPlayer(pl):
                return redirect(url_for('room_play'))
            flash('人满了')
            return render_template('lobby.html', form = joinForm, name = name)
        return render_template('lobby.html', form = joinForm, name = name)
    else:
        flash('游戏已经开始')
        return render_template('lobby.html', form = joinForm, name = name)

@app.route('/', methods=['GET', 'POST'])
def index():
    form = LoginForm()
    if form.validate_on_submit():
        if (pdb.exist(form.username.data)):
            if (pdb.check(form.username.data, form.password.data)):
                session['name'] = form.username.data
                return redirect(url_for('lobby'))
            else:
                session['name'] = None
                flash('用户名或密码错误')
        else:
            pdb.addPlayer(form.username.data, form.password.data)
            session['name'] = form.username.data
            return redirect(url_for('lobby'))
    return render_template('index.html', form=form)

##### QUICK TEST #####
@app.route('/test/host', methods=['GET'])
def test_host():
    global game
    n = 4
    #cfg = GameConfig(2, n-6, True, True, True, True, 'all')
    cfg = GameConfig(2, 2, False, False, False, False, 'all')

    # create players
    pdb.addPlayer('asdf', 'asdf')
    for i in range(n-1):
        pdb.addPlayer(f'p{str(i)}', f'p{str(i)}')
    #pdb.addPlayer('叶温乐', 'ywl') #pdb.addPlayer('董士纬', 'dsw')
    #pdb.addPlayer('徐瑞', 'xr') #pdb.addPlayer('林沈', 'ls')
    #pdb.addPlayer('尤诗超', 'usc') #pdb.addPlayer('阿玉', 'ay')
    #pdb.addPlayer('蛤', 'h')

    # start game
    game = Game()
    game.setConfig(cfg)
    game.state = Game.GST_WAIT_JOIN
    game.setHost(pdb.get('asdf'))
    for i in range(n-1):
        game.addPlayer(pdb.get(f'p{str(i)}'))
    #game.addPlayer(pdb.get('叶温乐')) #game.addPlayer(pdb.get('董士纬'))
    #game.addPlayer(pdb.get('徐瑞')) #game.addPlayer(pdb.get('林沈'))
    #game.addPlayer(pdb.get('尤诗超')) #game.addPlayer(pdb.get('阿玉'))
    #game.addPlayer(pdb.get('蛤'))

    # goto host
    session['name'] = 'asdf'
    return redirect(url_for('room_play'))

@app.route('/test/real', methods=['GET'])
def test_real():
    global game
    n = 8
    cfg = GameConfig(2, 2, True, True, True, True, 'all')

    # create players
    pdb.addPlayer('asdf', 'asdf')
    pdb.addPlayer('叶温乐', 'ywl'); pdb.addPlayer('董士纬', 'dsw')
    pdb.addPlayer('徐瑞', 'xr')   ; pdb.addPlayer('林沈', 'ls')
    pdb.addPlayer('尤诗超', 'usc'); pdb.addPlayer('阿玉', 'ay')
    pdb.addPlayer('蛤', 'h')

    # start game
    game = Game()
    game.setConfig(cfg)
    game.state = Game.GST_WAIT_JOIN
    game.setHost(pdb.get('asdf'))
    game.addPlayer(pdb.get('叶温乐')); game.addPlayer(pdb.get('董士纬'))
    game.addPlayer(pdb.get('徐瑞'))  ; game.addPlayer(pdb.get('林沈'))
    game.addPlayer(pdb.get('尤诗超')); game.addPlayer(pdb.get('阿玉'))
    game.addPlayer(pdb.get('蛤'))

    # goto host
    session['name'] = 'asdf'
    return redirect(url_for('room_play'))


@app.route('/haha/<name>', methods=['GET'])
def test_player(name):
    session['name'] = name
    return redirect(url_for(redirectAll(session, '')))

@app.route('/test/witch', methods=['GET'])
def test_witch():
    #game.deliver
    return redirect(url_for(redirectAll(session, '')))


if __name__ == '__main__':
    manager.run()
