from flask import Flask, request
from flask_restful import Api, Resource
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import json


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///db_vol/YaProducts.db'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
api = Api()

db = SQLAlchemy(app)

class Products(db.Model):
    __tablename__ = "products"
    id = db.Column(db.TEXT, primary_key=True)
    name = db.Column(db.TEXT, nullable=False)
    parentId = db.Column(db.TEXT, nullable=True)
    price = db.Column(db.INTEGER)
    type = db.Column(db.TEXT, nullable=False)
    date = db.Column(db.DATETIME, nullable=False)

    def __init__(self, data):
        self.id = data["id"]
        self.name = data["name"]
        self.type = data["type"]
        self.date = data["date"]
        self.parentId = data["parentId"]

    def __str__(self):
        return f"Product: {self.id}"

    def GetJson(self):
        data = {}
        data["id"] = self.id
        data["name"] = self.name
        data["type"] = self.type
        data["date"] = self.date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        data["parentId"] = self.parentId
        data["price"] = self.price
        return data

    def Update(self, data):
        self.id = data["id"]
        self.name = data["name"]
        self.type = data["type"]
        self.date = data["date"]
        self.parentId = data["parentId"]


def ChangeDate(obj, time):

    obj.date = time

    if obj.parentId == None:
        return

    obj = Products.query.filter_by(id=obj.parentId).first()
    ChangeDate(obj, time)




def GetDaughters(obj):

    sons = Products.query.filter_by(parentId=obj["id"]).all()
    if sons == []:
        obj["children"] = []
        obj["price"] = [obj["price"]]
        return obj

    tmp = list(map(lambda x: GetDaughters(x.GetJson()), sons))
    obj["children"] = [i for i in tmp]
    obj["price"] = []
    for i in tmp:
        for j in i["price"]:
            obj["price"].append(j)

    return obj


def GetPrice(obj):
    obj["price"] = sum(obj["price"]) // len(obj["price"])

    if obj["children"] == []:
        obj["children"] = None
        return

    for child in obj["children"]:
        GetPrice(child)


class Add(Resource):

    def post(self):
        try:
            for item in request.json["items"]:
                item["date"] = datetime.strptime(request.json["updateDate"], "%Y-%m-%dT%H:%M:%S.000Z")
                obj = Products.query.filter_by(id=item["id"]).first()

                if obj == None:
                    obj = Products(item)
                else:
                    obj.Update(item)
                if item["type"] == "OFFER":
                    obj.price = item["price"]

                ChangeDate(obj, item["date"])
                db.session.add(obj)
            db.session.commit()
            response = app.response_class(
                response=json.dumps({"status": "success"}),
                status=200,
                mimetype='application/json',
            )
            return response
        except Exception as ex:
            db.session.rollback()
            response = app.response_class(
                response=json.dumps({
                      "code": 400,
                      "message": "Validation Failed"
                    }),
                status=400,
                mimetype='application/json',
            )
            print(ex)
            return response

class Nodes(Resource):
    def get(self, prod_id):
        try:
            obj = Products.query.filter_by(id=prod_id).first()
            if obj is not None:
                obj = GetDaughters(obj.GetJson())
                GetPrice(obj)
                response = app.response_class(
                    response=json.dumps(obj),
                    status=200,
                    mimetype='application/json',
                )
                return response
            else:
                response = app.response_class(
                    response=json.dumps({
                        "code": 404,
                        "message": "Item not found"
                    }),
                    status=404,
                    mimetype='application/json',
                )
                return response
        except Exception as ex:
            response = app.response_class(
                response=json.dumps({
                      "code": 400,
                      "message": "Validation failed"
                    }),
                status=400,
                mimetype='application/json',
            )
            print(ex)
            return response

class Sales(Resource):
    def get(self):
        try:
            date = datetime.strptime(request.args["date"], "%Y-%m-%dT%H:%M:%S.000Z")
            obj = list(map(lambda x: x.GetJson(), Products.query.filter(date >= Products.date, Products.date >= date - timedelta(days=1)).all()))
            response = app.response_class(
                response=json.dumps(obj),
                status=200,
                mimetype='application/json',
            )
            return response
        except Exception as ex:
            response = app.response_class(
                response=json.dumps({
                    "code": 400,
                    "message": "Validation Failed"
                }),
                status=400,
                mimetype='application/json',
            )
            print(ex)
            return response

class test(Resource):
    def get(self):
        print(request.args)
        return 200

class Statistics(Resource):
    def get(self, prod_id):
        try:
            dateStart = datetime.strptime(request.args["dateStart"], "%Y-%m-%dT%H:%M:%S.000Z")
            dateEnd = datetime.strptime(request.args["dateEnd"], "%Y-%m-%dT%H:%M:%S.000Z")
            obj = Products.query.filter(Products.id == prod_id, Products.date >= dateStart, Products.date < dateEnd).first()
            if obj is not None:
                obj = GetDaughters(obj.GetJson())
                GetPrice(obj)
            response = app.response_class(
                response=json.dumps(obj),
                status=200,
                mimetype='application/json',
            )
            return response
        except Exception as ex:
            response = app.response_class(
                response=json.dumps({
                      "code": 400,
                      "message": "Validation Failed"
                    }),
                status=400,
                mimetype='application/json',
            )
            return response

def DeleteObj(obj):

    sons = Products.query.filter_by(parentId=obj.id).all()

    if sons == []:
        db.session.delete(obj)
        return

    for son in sons:
        DeleteObj(son)
        db.session.delete(son)

    db.session.delete(obj)
    return


class Destroy(Resource):
    def delete(self, prod_id):
        try:
            obj = Products.query.filter_by(id=prod_id).first()
            if obj is not None:
                DeleteObj(obj)
                db.session.commit()
                response = app.response_class(
                    status=200,
                    mimetype='application/json',
                )
                return response
            else:
                response = app.response_class(
                    response=json.dumps({
                        "code": 404,
                        "message": "Item not found"
                    }),
                    status=404,
                    mimetype='application/json',
                )
                return response
        except Exception as ex:
            print(ex)
            return 400


api.add_resource(Add, "/imports")
api.add_resource(Nodes, "/nodes/<string:prod_id>")
api.add_resource(test, "/test")
api.add_resource(Sales, "/sales")
api.add_resource(Statistics, "/node/<string:prod_id>/statistic")
api.add_resource(Destroy, "/delete/<string:prod_id>")
api.init_app(app)

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True, port=80, host="0.0.0.0")