var BrigUIApplication = angular.module('brigui', ['ngResource']).
    config(['$routeProvider', function($routeProvider) {
        $routeProvider.
            when('/', {templateUrl:'view/base.html'}).
            when('/system', {controller: 'SystemListController', templateUrl:'view/system-list.html'}).
            when('/system/:systemId', {controller: 'SystemInfoController', templateUrl:'view/system-info.html'}).
            when('/benchmark', {controller: 'BenchmarkListController', templateUrl:'view/benchmark-list.html'}).
            when('/benchmark/:benchmarkId', {controller: 'BenchmarkInfoController', templateUrl:'view/benchmark-info.html'}).
            otherwise({redirectTo:'/'});
    }]);

BrigUIApplication.factory('BenchmarkFactory', ['$resource', function($resource) {
    return $resource('http://127.0.0.1\\:8100/benchmarks/:benchmarkId', {}, {
        query: {method:'GET', params:{benchmarkId:''}}
    });
}]);

BrigUIApplication.controller('BenchmarkListController', ['$scope', '$http', 'BenchmarkFactory', function($scope, $http, BenchmarkFactory) {
    $scope.benchmarks = BenchmarkFactory.query();
}]);

BrigUIApplication.controller('BenchmarkInfoController', ['$scope', '$http', function($scope, $http) {

}]);

BrigUIApplication.controller('SystemListController', ['$scope', '$http', function($scope, $http) {

}]);

BrigUIApplication.controller('SystemInfoController', ['$scope', '$http', function($scope, $http) {

}]);
