(function () {
  var app = angular.module('timezones', ['ngRoute']);
  app.config(function ($routeProvider, $locationProvider) {
    $routeProvider
      .when('/timezones', {
        templateUrl:    'timezones.list.html',
        controller:     'timezones.list',
        reloadOnSearch: false
      })
      .when('/timezones/create', {
        templateUrl: 'timezones.edit.html',
        controller:  'timezones.create'
      })
      .when('/timezones/edit/:id', {
        templateUrl: 'timezones.edit.html',
        controller:  'timezones.edit'
      })
      .when('/register', {
        templateUrl: 'register.html',
        controller:  'register'
      })
      .when('/login', {
        templateUrl: 'login.html',
        controller:  'auth'
      })
      .otherwise({redirectTo: '/login'})
    ;
  });

  app.run(['CurrentTimeService', function (currentTimeService) {
    currentTimeService.resume();
  }]);


  app.factory('CurrentTimeService', ['$rootScope', '$timeout',
    function ($rootScope, $timeout) {
      return new Ticker($timeout, 200, function (current) {
        $rootScope.currentTime = current;
      });
    }]);

  function Ticker($timeout, interval, callback) {
    this.callback = callback;
    this.$timeout = $timeout;
    this.current = 0;
    this.paused = true;
    this.interval = interval;
  }

  Ticker.prototype.resume = function () {
    var self = this;
    if (self.paused) {
      self.paused = false;
    }
    self.$timeout(function () {
      self._tick();
    });
  };
  Ticker.prototype.pause = function () {
    this.paused = true;
  };
  Ticker.prototype._tick = function () {
    var self = this;
    if (!self.paused) {
      self.callback(new Date().getTime());
      self.$timeout(function () {
        self._tick();
      }, self.interval);
    }
  };


  app.factory('TimezoneService', ['$http', '$q', '$window', function ($http, $q, $window) {
    return new TimezoneService($http, $q, $window)
  }]);

  app.controller('auth', ['$scope', '$location', 'TimezoneService',
    function (self, $location, svc) {
      if (svc.isLoggedIn()) {
        $location.path('/timezones');
      }
      self.login_info = {
        ĺogin:    '',
        password: ''
      };
      self.do_login = function () {
        svc.login(self.login_info.login, self.login_info.password).then(
          function () {
            $location.path('/timezones');
          }
        );
      };
      self.logout = function () {
        svc.logout();
        $location.path('/login');
      }
    }]);

  app.controller("user", ['$scope', 'TimezoneService', 'AuthService',
    function (self, svc, auth) {
      self.user = {
        name:           '',
        login:          '',
        email:          '',
        password:       '',
        check_password: ''
      };
      //TODO: Validate password match
      //TODO: clear errors on retry
      self.register = function () {
        svc.register(self.user).then(function () {
          auth.login(self.user.login, self.user.password);
        });
      };
    }]);


  app.controller("timezones.list", ['$scope', 'TimezoneService', '$location',
    '$routeParams',
    function (self, svc, $location, $routeParams) {
      self.query = $routeParams.q || '';
      self.list = function () {
        var query = self.query;
        if (query === undefined || query === '') {
          query = null;
        }
        svc.list(self.query).then(function (timezones) {
          $location.search('q', query);
          self.timezones = timezones;
        });
      };
      self.edit = function (index) {
        $location.path('/timezones/edit/' + self.timezones[index].id)
      };
      self.remove = function (index) {
        svc.remove(self.timezones[index].id).then(function () {
          self.timezones.splice(index, 1);
        });
      };
      self.create = function () {
        $location.path('/timezones/create');
      };
      self.list();
    }
  ])
  ;

  app.controller("timezones.create", ['$scope', 'TimezoneService', '$location',
    function (self, svc, $location) {
      self.timezone = {
        city:              '',
        gmt_delta_seconds: 0
      };
      self.save = function () {
        svc.create(self.timezone).then(function () {
          $location.path('/timezones');
        });
      }
    }
  ]);
  app.controller("timezones.edit", ['$scope', 'TimezoneService', '$location',
    '$routeParams',
    function (self, svc, $location, $routeParams) {
      svc.get($routeParams.id).then(function (timezone) {
        self.timezone = timezone;
      });
      self.save = function () {
        svc.create(self.timezone).then(function () {
          $location.path('/timezones');
        });
      }
    }
  ]);

  app.filter('adjustTime', function () {
    return function (src, delta_seconds) {
      return src + delta_seconds * 1000;
    };
  });

  function TimezoneService(http, $q, $window) {
    var self = this;
    self.http = http;
    self.$q = $q;
    self.sessionStorage = $window.sessionStorage;
    self.localStorage = $window.localStorage;
    self.errors = [];
    self._token = null;
  }

  TimezoneService.prototype.req = function (method, url, data, headers) {
    var req = {
      method:  method,
      url:     url,
      data:    data,
      headers: headers
    };
    return this.http(req).then(function (response) {
      return response.data;
    });
  };

  TimezoneService.prototype.auth_req = function (method, url, data) {
    //TODO: check logged in or reject promise
    return this.req(method, url, data, { JWT: this.getToken() });
  };

  TimezoneService.prototype.id_ref = function (url, id) {
    return url + '/' + id;
  };

  TimezoneService.prototype.getToken = function () {
    return (
      this._auth_token ||
      this.sessionStorage.getItem('auth_token') ||
      this.localStorage.getItem('auth_token')
      );
  };
  TimezoneService.prototype.isLoggedIn = function () {
    return (this.getToken() !== null);
  };

  TimezoneService.prototype.setToken = function (token, durable) {
    this.localStorage.setItem('auth_token', token);
    if (durable) {
      this.sessionStorage.setItem('auth_token', token);
    }
  };
  TimezoneService.prototype.deleteToken = function () {
    this._token = null;
    this.sessionStorage.removeItem('auth_token');
    this.localStorage.removeItem('auth_token');
  };

  TimezoneService.prototype.login = function (login, password) {
    if (this.isLoggedIn()) {
      this.logout();
    }
    var self = this;
    return this.req('POST', '/auth', {login: login, password: password}).then(
      function (response) {
        self.setToken(response.token);
      });
  };

  TimezoneService.prototype.logout = function () {
    this.deleteToken();
  };


  TimezoneService.prototype.registerUser = function (data) {
    return this.auth_req('POST', '/users', data);
  };

  TimezoneService.prototype.list = function (query) {
    var path = '/timezones';
    if (query !== '') {
      path += '?q=' + encodeURIComponent(query);
    }
    return this.auth_req('GET', path);
  };

  TimezoneService.prototype.get = function (id) {
    return this.auth_req('GET', this.id_ref('/timezones', id));
  };
  TimezoneService.prototype.create = function (data) {
    return this.auth_req('POST', '/timezones', data);
  };
  TimezoneService.prototype.remove = function (id) {
    return this.auth_req('DELETE', this.id_ref('/timezones', id));
  };
  TimezoneService.prototype.update = function (id, data) {
    return this.auth_req('PUT', this.id_ref('/timezones', id), data);
  };

  app.directive("analogClock", function () {
    return {
      link:     function (scope, element, attrs) {
        var canvas = angular.element(element.children()[0])[0];
        scope.clock = new AnalogClock(canvas, 100);
        scope.$watch('time', function (time) {
          scope.clock.tick(time);
        });
      },
      scope:    {
        'time': '='
      },
      template: '<canvas></canvas>'
    };
  });

  var AnalogClock = function (canvas, size) {
    this.canvas = canvas;
    canvas.width = size;
    canvas.height = size;
    this.context2d = canvas.getContext('2d');
    this.size = size;
  };
  AnalogClock.prototype.tick = function (time) {
    if (typeof time === 'undefined') {
      return
    } else if (typeof time === "number") {
      time = new Date(time);
    }
    this.context2d.clearRect(0, 0, this.size, this.size);
    this.drawBase();
    this.drawTime(time);
  };
  AnalogClock.prototype.drawBase = function () {
    var c = this.context2d;
    var size = this.size;
    c.save();
    c.beginPath();
    c.lineWidth = size / 30;
    c.arc(size / 2, size / 2, size / 2 - 2 * c.lineWidth, 0, 2 * Math.PI, false);
    c.fillStyle = colors.main.solid[0];
    c.fill();
    c.strokeStyle = colors.main.solid[4];
    this.setShadow(c.lineWidth);
    c.closePath();
    c.stroke();
    c.restore();

    this.drawMarkers();
  };
  AnalogClock.prototype.drawMarkers = function () {
    var c = this.context2d;
    var size = this.size;
    var width = size / 60;
    c.save();
    c.translate(size / 2, size / 2);
    c.fillStyle = colors.main.solid[1];
    this.setShadow(width);

    for (var i = 0; i < 12; i++) {
      c.rotate(Math.PI / 6);
      c.fillRect(-width / 2, -size * 0.40, width, size / 12)
    }
    c.restore();
  };


  AnalogClock.prototype.drawTime = function (time) {
    var size = this.size;
    var hour = time.getHours() % 12;
    var pm = time.getHours() / 12 >= 1;
    var minute = time.getMinutes();
    hour += minute / 60;
    var second = time.getSeconds();
    minute += second / 60;

    this.drawHand(minute * Math.PI / 30, size / 40, size / 3,
      colors.main.solid[1]);
    this.drawHand(Math.PI / 2 + hour * Math.PI / 6, size / 25, size / 3.5,
      colors.main.solid[3]);
    this.drawHand(second * Math.PI / 30, size / 100, size / 2.5,
      colors.comp.solid[2]);
    this.drawHandCover(size / 40, colors.comp.solid[2]);


  };
  AnalogClock.prototype.drawHandCover = function (width, color) {
    var c = this.context2d;
    var size = this.size;
    c.save();
    c.translate(size / 2, size / 2);
    c.fillStyle = color;
    c.beginPath();
    c.arc(0, 0, width, 2 * Math.PI, false);
    c.fill();
    c.closePath();
    c.restore();
  };
  AnalogClock.prototype.setShadow = function (width) {
    var c = this.context2d;
    c.shadowBlur = width;
    c.shadowOffsetX = width / 2;
    c.shadowOffsetY = width / 2;
    c.shadowColor = colors.shadow;
  };
  AnalogClock.prototype.drawHand = function (angle, width, height, fill) {
    var c = this.context2d;
    var size = this.size;
    c.save();
    this.setShadow(width);
    c.fillStyle = fill;
    c.translate(size / 2, size / 2);
    c.rotate(angle);
    c.fillRect(-width / 2, -height, width, height);
    c.restore();
  };

  var colors = {
    main:      {
      solid:      [
        'rgba(188,204,228,  1)',
        'rgba( 78,118,176,  1)',
        'rgba( 28, 77,150,  1)',
        'rgba(  8, 43, 94,  1)',
        'rgba(  1, 17, 40,  1)'
      ],
      traslucent: [
        'rgba(188,204,228, .5)',
        'rgba( 78,118,176, .5)',
        'rgba( 28, 77,150, .5)',
        'rgba(  8, 43, 94, .5)',
        'rgba(  1, 17, 40, .5)'

      ]
    }, comp:   {
      solid:         [
        'rgba(255,237,205,  1)',
        'rgba(255,197, 99,  1)',
        'rgba(227,152, 24,  1)',
        'rgba(142, 90,  0,  1)',
        'rgba( 61, 38,  0,  1)'

      ], traslucent: [
        'rgba(255,237,205, .5)',
        'rgba(255,197, 99, .5)',
        'rgba(227,152, 24, .5)',
        'rgba(142, 90,  0, .5)',
        'rgba( 61, 38,  0, .5)'

      ]

    }, shadow: "rgba(0,0,0,0.2)"
  };

}
()
  )
;

