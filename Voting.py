#!/usr/bin/env python
# coding: utf-8
# require: kaleido

import streamlit as st
import pandas as pd
#import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
from fpdf import FPDF
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import dataframe_image as dfi
from datetime import datetime
import kaleido

######################################## Part 1. title ########################################
st.title("投票程式")

################################### Part 2. Configuration Setting ###################################
chart_flag = "Bar chart"
show_author = 'Show'
program_setting = st.sidebar.selectbox("程式設定", ['初次統計出席人數','上傳附加出席人數檔案及更新','計算投票結果'])

have_shareOption = st.sidebar.selectbox("業權份數存在非數字",['是','不是'])

if program_setting == '計算投票結果':
    question_type = st.sidebar.selectbox("問題題形",['是非題','多項選擇題'])
    
    vote_num = st.sidebar.number_input("議程編號", min_value=1, max_value=100, value=1, key=int)    

    if question_type == '多項選擇題':
    
        max_selection = st.sidebar.number_input("多項選擇題最大可選數量", min_value=1, max_value=100, value=1, key=int)    
        
    download_flag = st.sidebar.checkbox("下載結果成PDF")    
question_num = 1    
#question_num = st.sidebar.number_input("Total Questions in One Vote", min_value=1, value=1, key=int)   
#show_stat_detail = st.sidebar.selectbox("Show Detail Voting Stat",['Show', 'Do not show'])

################################### Part 3 Common Functions ###################################

# Upload file
###################################
def upload_a_file(file):
    df = pd.read_csv(file, header=0,
                     dtype={'Cancelid':object, 'AuthID':object, 'shareOption':object})

    return df
###################################

# Data Processing
###################################
def data_process(df):
    
    columns_list = list(df.columns)

    for i in columns_list:
        df.loc[df[i] == 'ERROR3100', i ] = None
        
    # deal with Yes_No_Question
    if question_type == '是非題':
        for i in range (1, int(question_num) + 1):
            q_name = 'q' + str(i)
            choice_name = '選項' + str(i) + "  "
            df.loc[df[q_name].isin(["Yes","YES"]), choice_name] = 'Yes'
            df.loc[df[q_name].isin(["No","NO"]), choice_name] = 'No'
            
            df.drop([q_name], axis = 1, inplace = True)
            
     # deal with Multiple Selections        
    elif question_type == '多項選擇題':
        all_ans_list_tmp = list(df['q1'])

        for i, item in enumerate(all_ans_list_tmp):
            if item != None:
                if item[0] == "(":
                    tmp = item[1:-1]
                    all_ans_list_tmp[i] = tmp.split(',')

        all_ans_list = []

        for i, item in enumerate(all_ans_list_tmp):
            if type(item) != list:
                tmp_list = [item]
                all_ans_list.append(tmp_list)

            elif len(item) <= max_selection:
                all_ans_list.append(item)
            #else:
                #all_ans_list.append("")

        temp_df = pd.DataFrame(all_ans_list, dtype = str)
        
        global len_of_y_axis
        len_of_y_axis = temp_df.shape[-1]
        len_of_y_axis_left = int(max_selection) - len_of_y_axis
        
        column_list = []
        for i in range(1, int(len_of_y_axis) + 1):
            choice_name = "選項" + str(i) + "  "
            column_list.append(choice_name)
        
        temp_df.columns = column_list
        df = pd.concat([df, temp_df], axis=1)
        
        df.drop(['q1'], axis=1, inplace= True)
       
    # find out votes with wrong Question number

    df_wrong_q = df.loc[~df['voteNum'].isin([vote_num])]
    df = df.loc[df['voteNum'].isin([vote_num])]
    
    # find out the cancelid 
    Cancelid_list = list(df.loc[df['Cancelid'].notnull()].Cancelid)
    
    #add manual input cancel id on list
#    if len(text_input) != 0:
#        for i in m_cancel_id:
#            Cancelid_list.append(i)
    
    #cancel id from dedeup_AuthID
    df_dedup_AuthID = pd.read_csv("./temp_csv/dedup_AuthID.csv", header=0, index_col=0,dtype={'AuthID':object})    

    df_dedup_AuthID['AuthID'] = df_dedup_AuthID['AuthID'].astype(str)
    dedup_AuthID_list = list(df_dedup_AuthID['AuthID'])
    
    for i in dedup_AuthID_list:
            Cancelid_list.append(i)            

    df = df.loc[df['Cancelid'].isnull()]

    # clear row with cancelid
    df_cancel = df.loc[df['AuthID'].isin(Cancelid_list)]    
    df = df.loc[~df['AuthID'].isin(Cancelid_list)]
   
    # clear row with wrong weights (both null / both not null)
    if have_shareOption == '是':

        mapping_table = pd.read_csv("./Mapping/Mapping_Table.csv", header=0,dtype={'Map_Option':object, 'Weight':float})
        
        df = pd.merge(df, mapping_table, how="left", on =['shareOption'])
    
        df_wrong_weight = df.loc[((df['shareOption_2'].notnull() & df['share'].notnull()) |(df['shareOption_2'].isnull() & df['share'].isnull()))]

        df = df.loc[~((df['shareOption_2'].notnull() & df['share'].notnull()) |
    (df['shareOption_2'].isnull() & df['share'].isnull()))]

        df.loc[df['shareOption_2'].notnull(), 'Weight'] = df['shareOption_2']
#        df.loc[df['shareOption_2'].isnull(), 'Weight'] = df['share']
        
        st.write(df) 
        
    elif have_shareOption == '不是':
        df_wrong_weight = df.loc[df['share'].isnull()]
        df = df.loc[df['share'].notnull()]
        
        df['Weight'] = df['share'].astype(float)
            
    # convert Choice with Null to Void
    if question_type == '是非題':
        df['Void_num'] = 0

        for i in range (1, int(question_num) + 1):
            choice_name = '選項' + str(i) + "  "
            df.loc[df[choice_name].isnull(), 'Void_num'] +=  1
            
        # all Choices are void
        df_choice_all_na = df.loc[df['Void_num'] == question_num]
        df = df.loc[df['Void_num'] != question_num]
            
    # deal with Multiple Selections        
    elif question_type == '多項選擇題':
        
        # convert Choice with Null to Void
        df['Void_num'] = 0
        
        #for i in range (1, int(max_selection) + 1):
        for i in range (1, int(len_of_y_axis) + 1):
            choice_name = '選項' + str(i) + "  "
            df.loc[df[choice_name].isnull(), 'Void_num'] +=  1
            df.loc[df[choice_name]=='BLANK', 'Void_num'] +=  1
            df.loc[df[choice_name]=='!', 'Void_num'] +=  1            
                   
        # all Choices are void
        df_choice_all_na = df.loc[df['Void_num'] == len_of_y_axis]
        df = df.loc[df['Void_num'] != len_of_y_axis]
        
    # summerize authorised votes
    df.loc[df['AuthID'].isnull(), '授權票   '] = 'N'
    df.loc[df['AuthID'].notnull(), '授權票   '] = 'Y'
    
    if have_shareOption == '是':
        df.drop(['voteNum','AuthID', 'Cancelid','shareOption','share','Void_num'], 
                axis = 1, inplace = True)
    elif have_shareOption == '不是':
        df.drop(['voteNum','AuthID', 'Cancelid','share','Void_num'], 
                axis = 1, inplace = True)
        
    # calculate the stat
    valid_amt = len(df.count(axis=1))
    author_amt = len(df.loc[df['授權票   '] == 'Y'].count(axis=1))
    non_author_amt = valid_amt - author_amt
    
    wrong_q_amt = len(df_wrong_q.count(axis=1))
    wrong_weight_amt = len(df_wrong_weight.count(axis=1))
    choice_all_na_amt = len(df_choice_all_na.count(axis=1))
    void_amt = wrong_q_amt + wrong_weight_amt + choice_all_na_amt
    
    cancel_amt = len(df_cancel.count(axis=1))
    
    total = valid_amt + void_amt + cancel_amt
    
    valid_amt_per = valid_amt / total * 100
    void_amt_per = void_amt / total * 100
    cancel_amt_per = cancel_amt / total *100
    total_amt_per = total / total * 100
    
    non_author_amt_per = non_author_amt / total * 100
    author_amt_per = author_amt / total * 100
    wrong_q_amt_per = wrong_q_amt / total * 100
    wrong_weight_amt_per = wrong_weight_amt / total * 100  
    choice_all_na_amt_per = choice_all_na_amt / total * 100
        
    # statistics df 
    df_stat_detail = pd.DataFrame([[non_author_amt, non_author_amt_per], 
                            [author_amt, author_amt_per],
                            [wrong_q_amt, wrong_q_amt_per],                                
                            [wrong_weight_amt, wrong_weight_amt_per],                                 
                            [choice_all_na_amt, choice_all_na_amt_per],                                
                            [cancel_amt, cancel_amt_per],
                            [total, total_amt_per]],
                          
                            index=['非授權票(有效)  ', 
                                   '授權票(有效)  ',
                                   '錯誤議程投票(無效)       ',
                                   '錯誤業權投票(無效)       ',
                                   '錯誤選擇投票(無效)       ',     
                                   '取消票數  ',
                                   '總票數  '],
                            columns=['投票數  ', '百份比(%)  '])
    
    df_stat_detail['百份比(%)  '] = df_stat_detail['百份比(%)  '].map('{:.2f}'.format)
    
    return df, df_stat_detail
###################################

# Show Voting Results
###################################
def show_results(df, choice_n):
    # append each choice's summed weight on score_list

    def bar_show_create_result(df_tmp):

        def gen_all_table (df_tmp, Char):
            table_name = df_tmp.loc[(df_tmp[choice_n]== i) & (df_tmp['授權票   ']== 'Y')]
            score = table_name['Weight'].sum()
            choice_list.append(Char)
            author_list.append('Y')
            score_list.append(score)
            
            table_name = df_tmp.loc[(df_tmp[choice_n]== i) & (df_tmp['授權票   ']== 'N')]
            score = table_name['Weight'].sum()
            
            choice_list.append(Char)
            author_list.append('N')
            score_list.append(score)
            
        # find distinct choices
        unique_choice = list(df_tmp[choice_n].unique())
        choice_list = []
        author_list = []
        score_list = []

        for i in unique_choice:
            gen_all_table(df_tmp, i)

        df_tmp2 = pd.DataFrame({
                             choice_n:choice_list,
                             '授權票   ': author_list,
                             '加權票數   ':score_list
                            })
        
        df_tmp2['百份比(%)  '] = df_tmp2['加權票數   '] / df_tmp2['加權票數   '].sum() * 100
        
        df_for_summary = df_tmp2.groupby(choice_n)['加權票數   ','百份比(%)  '].sum()

        df_for_summary = df_for_summary.reset_index()
        
        df_for_summary = df_for_summary.sort_values(by=['加權票數   '], ascending=False)
        
        df_for_summary['加權票數   '] = df_for_summary['加權票數   '].map('{:.3f}'.format)           
        df_for_summary['百份比(%)  '] = df_for_summary['百份比(%)  '].map('{:.2f}'.format)
        #df_tmp2['加權票數   '] = df_tmp2['加權票數   '].map('{:.0f}'.format)      
        df_tmp2['百份比(%)  '] = df_tmp2['百份比(%)  '].map('{:.2f}'.format)        
        
        df_tmp2['Text'] = df_tmp2['加權票數   '].astype(str) + ',  ' + df_tmp2['百份比(%)  '].astype(str) + '%'
        
        return df_tmp2, df_for_summary     

    df_result, df_result_summary = bar_show_create_result(df)

    fig_1 = px.bar(df_result, x=choice_n, y='加權票數   ', color='授權票   ', text='Text', title="")

    df_result['加權票數   '] = df_result['加權票數   '].map('{:.3f}'.format)       

    df_result.drop('Text', axis=1, inplace=True)
        
    fig_1.update_layout(showlegend=False)
    
    return fig_1, df_result, df_result_summary
###################################

############################## Part 4.1  程式設定=初次統計出席人數 ##############################
if program_setting == '初次統計出席人數':
#    sel_file = "./data/attendence_list.csv"
    sel_file = st.file_uploader("選擇初次統計出席人數")

    st.header("顯示結果")
    if st.button("顯示"):
        df = pd.read_csv(sel_file, header=0,
                             dtype={'Share':object, 
                                    'Owner': object, 
                                    'AuthID':object, 
                                    'Flat':object})

        df.to_csv("./temp_csv/latest_attendence.csv", encoding='utf-8')
        
        original_count_people_num = int(len(df.count(axis=1)))

        df_1 = df.loc[df['AuthID'].notnull()]
        df_2 = df.loc[~df['AuthID'].notnull()]

        df = pd.concat([df_2,df_1])
        df_dup = df.copy()

        df = df.drop_duplicates(subset=['Block','Floor','Flat'])
        
###########################################
# total_people_num = block * floor * flat #
# total_share_num needs to customize      #
###########################################

        total_table = pd.read_csv("./Mapping/Total_Table.csv", header=0,dtype={'total_people_num':float, 'total_share_num':float})
        
        total_people_num = total_table.iloc[0]['total_people']
        total_share_num = total_table.iloc[0]['total_share']
        
#Manually cancel ID        
#        Cancelid_list = list()

#        if len(text_input) != 0:
#            for i in m_cancel_id:
#                Cancelid_list.append(i)

#        df = df.loc[~df['AuthID'].isin(Cancelid_list)]        
        
#############################################################
# Manually map the Share to Share_int                       #
# eg, Share = A, then Share_int = 20 is:                    #
#     df.loc[df['Share'] == "A", 'Share_int'] = 20;         #
# warm reminder, should be 'Share' & 'Share_int'            #
#############################################################

#        df.loc[df['Share'] == "10", 'Share_int'] = 10;
#        df.loc[df['Share'] == "100", 'Share_int'] = 100;
#        df.loc[df['Share'] == "55", 'Share_int'] = 55;
#        df.loc[df['Share'] == "80", 'Share_int'] = 80;
#        df.loc[df['Share'] == "240", 'Share_int'] = 240;
#        df.loc[df['Share'] == "45", 'Share_int'] = 45;
#        df.loc[df['Share'] == "25", 'Share_int'] = 25;
#        df.loc[df['Share'] == "A", 'Share_int'] = 0.295;
#        df.loc[df['Share'] == "B", 'Share_int'] = 0.4;

        if have_shareOption == '是':

            mapping_table = pd.read_csv("./Mapping/Mapping_Table.csv", header=0,dtype={'Map_Option':object, 'Weight':float})
            
            df['shareOption'] = df['Share']
        
            df = pd.merge(df, mapping_table, how="left", on =['shareOption'])
                
        elif have_shareOption == '不是':

            df['shareOption_2'] = df['Share'].astype(float)

        count_people_num = int(len(df.count(axis=1)))
        count_share_num = float(df['shareOption_2'].sum())

        percent_people_num = "{:.2f}".format(count_people_num / total_people_num * 100)
        percent_share_num = "{:.2f}".format(count_share_num / total_share_num * 100) 

        df_visualization = pd.DataFrame([
                        [total_people_num, count_people_num, percent_people_num], 
                        [total_share_num, count_share_num, percent_share_num]],

                        index=['投票人數   ', '業權份數   '],
                        columns=['總人數/份數     ', '出席人數/份數     ', '人數/份數%     '])
        st.header("出席人數及業權份數統計")
        st.write(df_visualization)
        
        cancel_num_vote = str(original_count_people_num - count_people_num)
        st.write("取消授權票數為:", cancel_num_vote)
        
        df_distribution = pd.DataFrame([
                        [total_people_num, count_people_num, percent_people_num], 
                        [total_share_num, count_share_num, percent_share_num]],
                        columns=['Total', 'Present', 'Percent'],
                        index=['People','Share'])
        df_distribution.to_csv("./temp_csv/voting_distribution.csv", encoding='utf-8')
        
        df_dup['Floor'] = df_dup['Floor'].astype(str)
        df_dup['Concat_info'] = df_dup[['Block', 'Floor', 'Flat']].agg(''.join, axis=1)
        df_dup['Dup_ind'] = df_dup.duplicated(subset=['Concat_info'])
        df_dup2 = df_dup.copy()

        df_dup2 = df_dup2.loc[df_dup['Dup_ind'] == True]
        dup_concat_info = list(df_dup2['Concat_info'])
        
        df_dup = df_dup.loc[df_dup['Concat_info'].isin(dup_concat_info)]
        df_dup = df_dup.loc[df_dup['AuthID'].notnull()]
        df_dup = df_dup.drop(['Dup_ind','Concat_info'],axis=1)
        df_dup.to_csv("./temp_csv/dedup_AuthID.csv", encoding='utf-8')        
        
############################## Part 4.2  程式設定=上傳附加出席人數檔案及更新 ##############################
if program_setting == '上傳附加出席人數檔案及更新':
    update_attendence = st.file_uploader("選擇附加出席人數統計檔案")
    if st.button("上傳及更新"):

        df_latest_attendence = pd.read_csv('./temp_csv/latest_attendence.csv', header=0,
                                           dtype={'Share':object, 'Owner': object, 'AuthID':object, 'Flat':object})
        df_latest_attendence = df_latest_attendence.iloc[:,1:]

        df_update_attendence = pd.read_csv(update_attendence, header=0,
                                           dtype={'Share':object, 'Owner': object, 'AuthID':object, 'Flat':object})

        before_update_df = df_latest_attendence.drop_duplicates(subset=['Block','Floor','Flat'])
        before_update_count_people_num = int(len(before_update_df.count(axis=1)))

        df = pd.concat([df_latest_attendence, df_update_attendence])

        df = df.drop_duplicates()
        df.to_csv("./temp_csv/latest_attendence.csv", encoding='utf-8')

        original_count_people_num = int(len(df.count(axis=1)))

        df_1 = df.loc[df['AuthID'].notnull()]
        df_2 = df.loc[~df['AuthID'].notnull()]

        df = pd.concat([df_2,df_1])

        df_dup = df.copy()

        df = df.drop_duplicates(subset=['Block','Floor','Flat'])
        ###########################################
        # total_people_num = block * floor * flat #
        # total_share_num needs to customize      #
        ###########################################

        total_table = pd.read_csv("./Mapping/Total_Table.csv", header=0,dtype={'total_people_num':float, 'total_share_num':float})
        
        total_people_num = total_table.iloc[0]['total_people']
        total_share_num = total_table.iloc[0]['total_share']

#Manually cancel ID        
#        Cancelid_list = list()

#        if len(text_input) != 0:
#            for i in m_cancel_id:
#                Cancelid_list.append(i)

#        df = df.loc[~df['AuthID'].isin(Cancelid_list)]   

        #############################################################
        # forcely to add shareOption =1 since OMR cannot add Share  #
        # so that Share_int can be 21 in this case                  #
        #############################################################
        #    df['Share'] = "1"

        if have_shareOption == '是':

            mapping_table = pd.read_csv("./Mapping/Mapping_Table.csv", header=0,dtype={'Map_Option':object, 'Weight':float})
            
            df['shareOption'] = df['Share']
        
            df = pd.merge(df, mapping_table, how="left", on =['shareOption'])
                
        elif have_shareOption == '不是':

            df['shareOption_2'] = df['Share'].astype(float)

        count_people_num = int(len(df.count(axis=1)))
        count_share_num = float(df['shareOption_2'].sum())

        percent_people_num = "{:.2f}".format(count_people_num / total_people_num * 100)
        percent_share_num = "{:.2f}".format(count_share_num / total_share_num * 100) 

        df_visualization = pd.DataFrame([
                        [total_people_num, count_people_num, percent_people_num], 
                        [total_share_num, count_share_num, percent_share_num]],

                        index=['投票人數   ', '業權份數   '],
                        columns=['總人數/份數     ', '出席人數/份數     ', '人數/份數%     '])
        st.header("出席人數及業權份數統計")
        st.write(df_visualization)

        cancel_num_vote = str(original_count_people_num - count_people_num)
        st.write("取消授權票數為:", cancel_num_vote)

        new_add_vote = str(count_people_num - before_update_count_people_num)
        st.write("新增票數為:",new_add_vote)

        df_distribution = pd.DataFrame([
                        [total_people_num, count_people_num, percent_people_num], 
                        [total_share_num, count_share_num, percent_share_num]],
                        columns=['Total', 'Present', 'Percent'],
                        index=['People','Share'])
        df_distribution.to_csv("./temp_csv/voting_distribution.csv", encoding='utf-8')

        df_dup['Floor'] = df_dup['Floor'].astype(str)
        df_dup['Concat_info'] = df_dup[['Block', 'Floor', 'Flat']].agg(''.join, axis=1)
        df_dup['Dup_ind'] = df_dup.duplicated(subset=['Concat_info'])
        df_dup2 = df_dup.copy()

        df_dup2 = df_dup2.loc[df_dup['Dup_ind'] == True]
        dup_concat_info = list(df_dup2['Concat_info'])

        df_dup = df_dup.loc[df_dup['Concat_info'].isin(dup_concat_info)]
        df_dup = df_dup.loc[df_dup['AuthID'].notnull()]
        df_dup = df_dup.drop(['Dup_ind','Concat_info'],axis=1)
        df_dup.to_csv("temp_csv/dedup_AuthID.csv", encoding='utf-8')

############################## Part 4.3  程式設定=計算投票結果 ##############################
if program_setting == '計算投票結果':
    sel_file = st.file_uploader("選擇投票檔案")
    
    st.header("顯示結果")
    if st.button("顯示"):
        
        df_show_distribution = pd.read_csv("./temp_csv/voting_distribution.csv", header=0, index_col = 0)

###########################################
# (Un)comment to (un)show the distrution  #
###########################################

        df_show_distribution.rename(columns={"Total":"總人數/份數       ",
                                         "Present":"出席人數/份數       ",
                                         "Percent":"人數/份數%       "}, 
                                index = {"People":"投票人數    ",
                                         "Share":"業權份數    "},inplace=True) 

        st.header("出席人數及業權份數統計")
        st.write(df_show_distribution)
        
        if sel_file is not None:
            df_raw = upload_a_file(sel_file)

#############################################################
# forcely to add shareOption =1 since OMR cannot add Share  #
# so that Share_int can be 21 in this case                  #
#############################################################

#            df_raw['shareOption'] = "1"

            for i in range(1, int(question_num)+1):
                q_name = 'q' + str(i)
                df_raw[q_name] = df_raw[q_name].apply(str)
                df_raw.loc[df_raw[q_name]=='nan', q_name] = '!'

            df_raw.loc[df_raw['share'].isin(['*','**','***','****']),'share'] = None

            #temp use
            df_raw = df_raw.loc[~df_raw['q1'].isin(['BLANK'])]

            df_clear, stat_detail = data_process(df_raw)

            if question_type == "Selection_Question":
                for i in range(1, int(len_of_y_axis)+1):
                    choice_name = "選項" + str(i) + "  "
                    df_temp = df_clear[[choice_name, 'Weight','授權票   ']]
                    df_temp.rename(columns={choice_name:"MC"}, inplace=True)
                    df_temp = df_temp.loc[df_temp['MC'].notnull()]
                    if i == 1:
                        df_insert = df_temp
                    else:
                        df_insert = pd.concat([df_insert,df_temp])

                df_insert.rename(columns={"MC":"選項1  "}, inplace=True)    
                df_clear = df_insert

            fig_list = []
            df_list = []
            df_s_list = []

            for i in range(1, int(question_num) + 1):
                choice_name = "選項" + str(i) + "  "
                df_temp = df_clear.loc[df_clear[choice_name].notnull()]

                fig_f, df_f, df_s_f = show_results(df_temp, choice_name)

                fig_list.append(fig_f)
                df_list.append(df_f)
                df_s_list.append(df_s_f)
            st.header("投票數據統計")
            st.write(stat_detail)

        for i in range(0, int(question_num)):
            Q = "問題 " + str(i+1)
            st.header(Q)        
            st.header("投票結果圖表")
            st.plotly_chart(fig_list[i])
            st.header("投票結果數據統計")   
            st.write(df_list[i])        
            st.header("投票結果數據總結")
            st.write(df_s_list[i])
           
        #generate PDF report
        if download_flag:
            
            #fig_f.write_image("./temp_png/pic1.png",engine="orca") 
            fig_f.write_image("./temp_png/pic1.png") 
            dfi.export(df_list[i], "./temp_png/pic2.png")
            dfi.export(df_s_list[i], "./temp_png/pic3.png")
            
            pdf = FPDF()
            pdf.add_font('fireflysung','','fireflysung.ttf',True)
            pdf.add_page()
            pdf.set_font('fireflysung',size=9)
            pdf.text(20,10,Q)
            pdf.text(20,20,"投票結果圖表")
            pdf.image("./temp_png/pic1.png",20,40,w=190)
            
            pdf.add_page()            
            pdf.text(20, 20, "投票結果數據統計")
            pdf.image("./temp_png/pic2.png",20,25,w=45)
            
            pdf.add_page()
            pdf.text(20, 20, "投票結果數據總結")
            pdf.image("./temp_png/pic3.png",20,25,w=45)
            
            now = datetime.now()
            now_string = now.strftime("%d_%m_%Y_%H%M%S")
            
            pdf.output('./report/agenda{}_{}.pdf'.format(vote_num, now_string))
            
            st.write("投票結果PDF成功下載")
        

