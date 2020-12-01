import jwt
import bcrypt
from datetime import datetime, timedelta

from util.exception import NotExistsException, ExistsException, InvalidValueException
from config         import SECRET, ALGORITHM


class UserService:
    def __init__(self, user_dao):
        self.user_dao = user_dao

    def sign_up(self, db, data):
        """
        유저 회원가입
        이미 존재하는 아이디는 확인 후 예외처리,
        패스워드는 암호화하여 DB에 저장
        :param db: db_connection
        :param data: 회원가입 정보
        """

        if self.user_dao.check_account(db, data):
            raise ExistsException('already existed account', 409)

        hashed_pw = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
        data['password'] = hashed_pw.decode('utf-8')

        seller_id = self.user_dao.sign_up(db, data)

        self.user_dao.create_seller_information(db, seller_id)
        
        # 로그 테이블 생성
        user_info = self.user_dao.get_seller_information(db, seller_id)
        self.user_dao.create_seller_logs(db, user_info)

    def sign_in(self, db, data):
        """
        유저 로그인
        해당 유저가 존재하는지 체크하고 패스워드 일치 여부 확인,
        access_token 발급
        :param db: db_connection
        :param data: account(계정이름), password
        :return: access_token
        """

        user_id = self.user_dao.check_account(db, data)

        if not user_id:
            raise NotExistsException('not exists account', 400)

        user_info = self.user_dao.sign_in(db, data)

        if not bcrypt.checkpw(data['password'].encode('utf-8'), user_info['password'].encode('utf-8')):
            raise NotExistsException('invalid account', 400)

        # exp = datetime.utcnow() + timedelta(minutes=30)
        exp = datetime.utcnow() + timedelta(days=1)
        access_token = jwt.encode({'account' : user_info['account'], 'exp' : exp}, SECRET, algorithm=ALGORITHM)

        return access_token.decode('utf-8')

    def seller_category_type(self, db):
        """
        셀러 카테고리 정보 가져오기
        :param db: db_connection
        :return: 카테고리 리스트
        """

        category = self.user_dao.seller_category_type(db)
        return category

    def get_seller_list(self, db, filters):
        """
        셀러 회원 목록 가져오기
        :param filters: 회원 목록 필터
        :param db: db_connection
        :return: 셀러 회원 목록
        """

        filters['offset'] = int(filters['offset']) if 'offset' in filters else 0
        filters['limit']  = int(filters['limit']) if 'limit' in filters else 10

        if filters['offset'] > filters['limit']:
            raise InvalidValueException('offset should not greater than limit', 400)

        count     = self.user_dao.get_seller_list_count(db, filters)
        user_info = self.user_dao.get_seller_list(db, filters)

        sellers = {
            'count'       : count['count'],
            'seller_list' : user_info
        }

        return sellers

    def get_seller_information(self, db, seller_id):
        """
        셀러 상세정보 가져오기
        :param db: db_connection
        :param seller_id: seller_id
        :return: 셀러 상세정보
        """

        user_info = self.user_dao.get_seller_information(db, seller_id)
        managers  = self.user_dao.get_managers(db, seller_id)

        if not user_info:
            raise NotExistsException('not exists seller', 400)

        user_info['managers'] = managers

        return user_info

    def update_seller_information(self, db, data, seller_id, modifier_id):
        """
        셀러 상세정보 수정
        담당매니저를 3개이상 등록하려고할 경우는 예외처리
        담당매니저 부분은 기존의 데이터와 비교해서 수정하거나 생성,삭제 처리
        :param db: db_connection
        :param data: 셀러 상세정보
        :param modifier_id: modifier_id (수정자)
        :param seller_id: seller_id
        """

        ordering = self.user_dao.get_ordering_managers(db, seller_id)
        if ordering:  # 기존에 매니저가 존재했는지 체크
            if data['managers']:  # 기존에 매니저가 존재하고, request 에도 있는 경우
                if len(data['managers']) > 3:  # 리스트를 3개 이상 요청했을 경우
                    raise InvalidValueException('managers are the maximum of 3', 400)

                row_count = ordering['ordering']
                input_count = len(data['managers'])

                order_index = 1
                if row_count == input_count:  # 기존의 개수와 똑같은 경우 (수정)
                    for manager_info in data['managers']:
                        manager_info['seller_id'] = seller_id
                        manager_info['ordering'] = order_index
                        self.user_dao.update_managers(db, manager_info)
                        order_index += 1

                elif row_count > input_count:  # 기존의 개수가 더 많을 경우 (수정->삭제)
                    for manager_info in data['managers']:
                        manager_info['seller_id'] = seller_id
                        manager_info['ordering'] = order_index
                        self.user_dao.update_managers(db, manager_info)
                        order_index += 1

                    for i in range(row_count - input_count):
                        manager_info = {
                            'seller_id' : seller_id,
                            'ordering'  : order_index
                        }
                        self.user_dao.delete_managers(db, manager_info)
                        order_index += 1

                elif row_count < input_count:  # 기존의 개수가 더 적을 경우 (수정->생성)
                    for i in range(row_count):
                        manager_info = data['managers'][i]
                        manager_info['seller_id'] = seller_id
                        manager_info['ordering'] = order_index
                        self.user_dao.update_managers(db, manager_info)
                        order_index += 1

                    for manager_info in data['managers'][order_index - 1:input_count]:
                        manager_info['seller_id'] = seller_id
                        manager_info['ordering'] = order_index
                        self.user_dao.create_managers(db, manager_info)
                        order_index += 1

            else:  # 기존에 존재했으나, request 에는 없는 경우 (삭제)
                row_count = ordering['ordering']

                for order_index in range(1, row_count + 1):
                    manager_info = {
                        'seller_id' : seller_id,
                        'ordering'  : order_index
                    }
                    self.user_dao.delete_managers(db, manager_info)
        else:  # 기존에는 존재하지 않는 경우 (생성)
            order_index = 1
            for manager_info in data['managers']:
                manager_info['seller_id'] = seller_id
                manager_info['ordering'] = order_index
                self.user_dao.create_managers(db, manager_info)
                order_index += 1

        data.pop('managers')
        data['seller_id'] = seller_id
        data['modifier_id'] = modifier_id
        self.user_dao.update_seller_information(db, data)

        # 로그 생성
        user_log = self.user_dao.get_seller_logs(db, seller_id)
        for key in data:
            user_log[key] = data[key]

        self.user_dao.create_seller_logs(db, user_log)

    def update_shop_status(self, db, data, seller_id):
        """
        셀러 상태(입점상태) 수정
        존재하지않는 상태값(id)일 경우 not exists shop_status
        현재 상태에 맞지 않는 상태 값을 요청시 invalid shop_status_id
        :param db: db_connection
        :param data: 셀러 상태
        :param seller_id: seller_id
        """

        data['seller_id'] = seller_id
        shop_status_type = self.user_dao.check_shop_status(db, data['shop_status_id'])

        # 존재하지 않는 shop_status_id
        if not shop_status_type:
            raise NotExistsException('not exists shop_status_id', 400)

        seller_status = self.user_dao.get_shop_status(db, seller_id)
        seller_status_id = seller_status['shop_status_id']

        # 현재 상태에 따른 상태 변경 exception
        if seller_status_id == 1:  # 입점대기
            if data['shop_status_id'] != 2:
                raise InvalidValueException('invalid shop_status_id', 400)

        elif seller_status_id == 2:  # 입점
            if data['shop_status_id'] != 4 and data['shop_status_id'] != 5:
                raise InvalidValueException('invalid shop_status_id', 400)

        elif seller_status_id == 3:  # 퇴점
            raise InvalidValueException('invalid shop_status_id', 400)

        elif seller_status_id == 4:  # 퇴점대기
            if data['shop_status_id'] != 2 and data['shop_status_id'] != 5 \
                    and data['shop_status_id'] != 3:
                raise InvalidValueException('invalid shop_status_id', 400)

        elif seller_status_id == 5:  # 휴점
            if data['shop_status_id'] != 2 and data['shop_status_id'] != 4:
                raise InvalidValueException('invalid shop_status_id', 400)

        self.user_dao.update_shop_status(db, data)
        
        # 로그 생성
        user_log = self.user_dao.get_seller_logs(db, seller_id)
        for key in data:
            user_log[key] = data[key]

        self.user_dao.create_seller_logs(db, user_log)

    def get_seller_status_log(self, db, seller_id):
        """
        셀러 상세 히스토리 정보 조회
        :param db: db_connection
        :param seller_id: seller_id
        :return: 상세 히스토리 리스트(시간, 입점상태, 수정자)
        """

        user_log = self.user_dao.get_seller_status_log(db, seller_id)
        log_list = [{
            'no'          : int(log['no']),
            'created_at'  : log['created_at'],
            'shop_status' : log['shop_status'],
            'modifier'    : log['modifier']
        } for log in user_log]

        return log_list
