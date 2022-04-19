window.onload = function(){
	localStorage.removeItem('started');
	localStorage.removeItem('items_to_show');

}

odoo.define('ping_order_dispaly.order_dashboard', function (require) {
"use strict";

var core = require('web.core');
var KanbanRecord = require('web_kanban.Record');
var Model = require('web.Model');
var _t = core._t;
var KanbanView = require('web_kanban.KanbanView');

KanbanView.include({
	events: _.defaults({
       'click .test_button': 'on_sales_team_target_click',
    }, KanbanView.prototype.events),
	init:function(){
		var self=this;
		this._super.apply(this, arguments);
		if(this.model == 'sale.order'){
			self.adjust_labels();

				if(localStorage.getItem('started')){
					//alert(self.inter)
					var items_to_show = localStorage.getItem('items_to_show');
					setTimeout(function(){
						$('.o_kanban_group[data-id="no"]').children('.oe_kanban_card').each(function($index){
							if($index >= items_to_show)
							$(this).addClass('hide_card');
						});
						$('.o_kanban_group[data-id="to invoice"]').children('.oe_kanban_card').each(function($index){
							if($index >= items_to_show)
							$(this).addClass('hide_card');
						});
						self.current_item = 0;
						self.current_item_to_invoice = 0;
						self.total_length = $('.o_kanban_group[data-id="no"]').children('.oe_kanban_card').length;
						self.total_length_to_invoice = $('.o_kanban_group[data-id="to invoice"]').children('.oe_kanban_card').length;

					},400);
					
					
				}
				else {
			
					self.loop_orders();
				}
		}
		
	},
	hide_all:function(){
			
		$('.o_kanban_group[data-id="no"]').children('.oe_kanban_card').each(function(){
			$(this).addClass('hide_card');
		});

	

	},
	hide_all_to_invoice:function(){
			
		$('.o_kanban_group[data-id="to invoice"]').children('.oe_kanban_card').each(function(){
			$(this).addClass('hide_card');
		});

	

	},
	
	adjust_labels:function(){
		setTimeout(function(){
			$('.o_kanban_group[data-id="no"] .o_kanban_header').find('.o_column_title').text('Sedang Proses');
			$('.o_kanban_group[data-id="to invoice"] .o_kanban_header').find('.o_column_title').text('Sudah Dapat Dibayar');
		},500);
	},
	 loop_orders:function(){

	 	var self=this;

    	this.items_to_show=3;
    	this.current_item= 0;
    	this.current_item_to_invoice= 0;
    	self.total_length = 0;
    	setTimeout(function(){
		//$('.oe_kanban_card').addClass('hide_card');
			self.hide_all();
			self.hide_all_to_invoice();
			self.total_length = $('.o_kanban_group[data-id="no"]').children('.oe_kanban_card').length;
			self.total_length_to_invoice = $('.o_kanban_group[data-id="to invoice"]').children('.oe_kanban_card').length;
    		var current_timer=0;
        	var interval = 0;
        		
         	new Model('sale.order').call('get_refresh_interval', [current_timer]).then(function (res) {
               var result = res.split(',');
               interval = parseFloat(result[0])*60*1000;
				self.items_to_show=parseInt(result[1]);
				localStorage.setItem('items_to_show', result[1]);
				$('.o_kanban_group[data-id="no"]').children('.oe_kanban_card').slice(self.current_item,self.current_item + self.items_to_show).each(function(){
					$(this).removeClass('hide_card');
				});
				self.loop_no =  setInterval(function(){

					self.hide_all();

					self.total_length = $('.o_kanban_group[data-id="no"]').children('.oe_kanban_card').length;


				   	if(self.current_item + self.items_to_show >= self.total_length){
						self.current_item = 0;
				   	}
				   	else {
				   		self.current_item = self.current_item + self.items_to_show;
				   	}

						$('.o_kanban_group[data-id="no"]').children('.oe_kanban_card').slice(self.current_item,self.current_item + self.items_to_show).each(function(){
						$(this).removeClass('hide_card');
					});
				},interval);
				$('.o_kanban_group[data-id="to invoice"]').children('.oe_kanban_card').slice(self.current_item_to_invoice,self.current_item_to_invoice + self.items_to_show).each(function(){
					$(this).removeClass('hide_card');
				});
				self.loop_to_invoice =  setInterval(function(){

					self.hide_all_to_invoice();

					self.total_length_to_invoice = $('.o_kanban_group[data-id="to invoice"]').children('.oe_kanban_card').length;


				   	if(self.current_item_to_invoice + self.items_to_show >= self.total_length_to_invoice){
						self.current_item_to_invoice = 0;
				   	}
				   	else {
				   		self.current_item_to_invoice = self.current_item_to_invoice + self.items_to_show;
				   	}

						$('.o_kanban_group[data-id="to invoice"]').children('.oe_kanban_card').slice(self.current_item_to_invoice,self.current_item_to_invoice + self.items_to_show).each(function(){
						$(this).removeClass('hide_card');
					});

				},interval);

                });


    	},500)

    	localStorage.setItem('started', 'yes');
    	

    },
   
   
    
});


});
